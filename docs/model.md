# Model description

This document lists the equations each module implements. Symbols are defined where they first appear. Parameter values are not repeated here; they are in `config.yaml`, which also gives the source of each one.

Throughout, $h(x) = -x\log_2 x - (1-x)\log_2(1-x)$ is the binary entropy and $H(p) = -\sum_i p_i \log_2 p_i$ is the Shannon entropy of a probability vector.

## Pair states and information: `src/core.py`

### Bell states and Bell-diagonal states

The four Bell states are generated from $|\Phi^+\rangle = (|00\rangle + |11\rangle)/\sqrt{2}$ by a Pauli operation on the first qubit:

$$|B_i\rangle = (P_i \otimes I)\,|\Phi^+\rangle, \qquad P_0 = I,\; P_1 = X,\; P_2 = Z,\; P_3 = XZ.$$

A shared pair is described by a Bell-diagonal state with weights $p = (p_0, p_1, p_2, p_3)$:

$$\rho_{AB} = \sum_i p_i\, |B_i\rangle\langle B_i|.$$

A Werner state of fidelity $F$ has $p = (F, r, r, r)$ with $r = (1-F)/3$.

The eavesdropper, Eve, is given the purification of the pair (`bell_diag_purification`):

$$|\psi\rangle_{ABE} = \sum_i \sqrt{p_i}\, |B_i\rangle_{AB} |i\rangle_E .$$

### Error rates and the CHSH value

The error rates in the Z and X bases are (`qber_from_weights`)

$$e_z = p_1 + p_3, \qquad e_x = p_2 + p_3 .$$

The CHSH value is (`chsh_from_weights`)

$$S = \sqrt{2}\,\big(|p_0 - p_1 - p_2 + p_3| + |p_0 + p_1 - p_2 - p_3|\big),$$

which for a Werner state is $S = 2\sqrt{2}\,(4F-1)/3$. The code only uses this function with Werner states.

### Key rates per pair

Three levels of certification give three secret fractions:

| Certification | Function | Secret fraction per pair |
| --- | --- | --- |
| Tomographic (all four weights known) | `key_rate_tomographic` | $\max(0,\, 1 - H(p))$ |
| BBM92 (two error rates known) | `key_rate_bbm92` | $\max(0,\, 1 - h(e_x) - h(e_z))$ |
| Device-independent (CHSH value and error rate $Q$) | `key_rate_di` | $\max\!\big(0,\, 1 - h(Q) - h\big(\tfrac{1 + \sqrt{(S/2)^2 - 1}}{2}\big)\big)$, and 0 if $S \le 2$ |

### Superdense coding

`sdc_information(p, q)` computes the information exactly. Alice applies one of the four Pauli operations with equal probability to her half. The encoded qubit crosses a depolarizing channel of strength $q$, which applies $X$, $Y$ or $Z$ each with probability $q/4$. Bob then measures in the Bell basis.

- $I_{AB}$ is the mutual information between Alice's choice and Bob's outcome. With a complete Bell measurement it equals $2 - H(p \circ q)$, where $p \circ q$ is the vector of Bell weights after the return channel.
- $\chi_E$ is Eve's Holevo information, $\chi = S(\bar\rho) - \tfrac14\sum_k S(\rho_k)$, where $S$ is the von Neumann entropy and $\rho_k$ is Eve's state for encoding $k$. It is computed for two cases. In the passive case Eve holds the purification and the environment of the return channel. In the intercept case she holds the purification and the encoded qubit itself.

In both cases $\chi_E \le H(p)$, which is checked numerically in the tests.

`sdc_linear_optics(p, q)` treats a Bell measurement made with linear optics, which separates only three classes of Bell states. Alice then uses three of the four encodings, and $I_{AB} \le \log_2 3$.

### Finite-key penalty

`finite_key_penalty(n)` returns the correction per pair for a block of $n$ pairs and security parameter $\varepsilon$:

$$\Delta(n) = 7\sqrt{\frac{\log_2(2/\varepsilon)}{n}} .$$

## Links and transports: `src/transports.py`

### Link model

`Link` holds the parameters of one link. For a fibre of length $L$ with attenuation $\alpha$ in dB/km, the transmission is

$$\eta_f(L) = 10^{-\alpha L/10} .$$

The error rate of a pair after one leg (`leg_qber`) combines misalignment and dark counts. With signal probability $s = \mu\,\eta\,\eta_d$ and noise probability $n = 2p_{\text{dark}}$,

$$Q = \frac{e_{\text{mis}}\, s + \tfrac12 n}{s + n},$$

where $\mu$ is the mean number of pairs per pulse, $\eta_d$ the detector efficiency, $p_{\text{dark}}$ the dark-count probability and $e_{\text{mis}}$ the misalignment error.

The pair is then modelled as a Werner state with $F = \max(\tfrac14,\, 1 - \tfrac32 Q)$ (`werner_from_qber`), and a leg with error rate $Q$ acts as a depolarizing channel of strength $\min(1, 2Q)$ (`depol_from_qber`).

`compose(p, q)` returns $p \circ q$, the Bell weights after a depolarizing channel of strength $q$ on one half.

### Secure bits per pair

`key_per_pair(p, cert)` returns the secret fraction $r_K$ from the table above. For the device-independent case it uses $V = (4p_0 - 1)/3$, $S = 2\sqrt{2}V$ and $Q = (1-V)/2$.

`sdc_per_pair(p, q, cert)` returns the secure bits per pair in superdense mode with a complete Bell measurement:

$$r_D = \max\!\big(0,\; 2 - H(p \circ q) - E\big),$$

where $E$ is the bound on Eve's information. With tomographic certification $E = H(p)$. With BBM92 certification $E$ is the largest entropy of any Bell-diagonal state with the measured $e_z$ and $e_x$, found by a grid search (`worst_entropy_given_qber`).

With a noiseless return leg and tomographic certification, $r_D = 2 - 2H(p) = 2 r_K$.

### Rates against distance

`rates_at(L, lk, cert, dist)` returns the secure rate of each transport at distance $L$. Let $\nu$ be the clock rate and $\eta = \eta_f(L)$. Three ways of distributing the pairs are modelled:

| Distribution | Pairs arriving per second | Verified pair rate $P$ | Error rate of the pair |
| --- | --- | --- | --- |
| Direct | $a = \nu\mu\eta$ | $a\,\eta_d^2$ | $Q(\eta)$ |
| Measurement-device-independent, with a relay at the midpoint | $a = \nu\mu\,(\eta_f(L/2)\,\eta_d)^2\, b$ | $a\,\eta_d^2$ | $\min(\tfrac12,\, 2Q(\eta_f(L/2)))$ |
| Heralded, device-independent | $a = R_{\text{DI}}\,\eta$ | $a$ | fixed |

Here $b$ is the Bell-measurement efficiency and $R_{\text{DI}}$ the heralding rate at zero distance.

Key mode gives

$$R_K = P\,\max(0,\, r_K - \Delta),$$

where $\Delta$ is the finite-key penalty, used only when `finite=True`.

In superdense mode Bob stores his half in a quantum memory while Alice's encoded half returns. The storage time is $t = 2L/c + t_{\text{check}}$, with $c$ the speed of light in fibre, and the memory adds depolarization $q_{\text{mem}} = 1 - e^{-t/T_2}$ (`mem_depol`). The return leg then has total depolarization $q = \min(1,\, 2Q(\eta) + q_{\text{mem}})$ and transmission $\eta_2 = \eta\,\eta_m\,\eta_d^2$, where $\eta_m$ is the memory efficiency. The two-step superdense rate is

$$R_D = a\,\eta_2\,\max(0,\, r_D - 2\Delta) .$$

The adaptive switch takes $\max(R_K, R_D)$.

Two transports that send a photon out and back without a prior check are also modelled. With round-trip transmission $\eta_{rt} = (\eta\,\eta_d)^2$ and error rate $Q_{rt} = \min(\tfrac12, 2Q(\eta))$,

$$R_{\text{DL04}} = \nu\mu\,\eta_{rt}\,\max(0,\, 1 - 2h(Q_{rt})),$$

and the ping-pong protocol has the same expression but gives zero unless $\eta_{rt}$ exceeds the security bound of 0.75.

### Switching threshold

Superdense mode is better when $\eta\, r_D > r_K$, where $\eta$ is the fraction of encoded photons that return. The threshold is (`switch_threshold_eta`)

$$\eta^* = \frac{r_K}{r_D} = \frac{1 - H(p)}{2 - H(p \circ q) - H(p)},$$

which equals $\tfrac12$ when the return leg is noiseless.

## Attack detection: `src/detect.py`

### Telemetry

`telemetry(T, seed)` generates one sample per second. All of it is synthetic.

- Polarization drift adds to the X-basis error: $d(t) = a_d\,(1 + \sin(2\pi t/T_d + \phi)) + w(t)$, where $w$ is a bounded random walk.
- Noise bursts start at random times and multiply the noise count rate: $n(t) = D_0\,(1 + m(t))$, where $m$ is the burst size.
- The accidental fraction is $f(t) = n/(n + C)$ with $C$ a reference signal level. The error probabilities are $e_z = e_0 + \tfrac12 f$ and $e_x = e_0 + d + \tfrac12 f$.
- Attacks start at random times, last a random duration and have a random strength $s$. Each of three types changes the telemetry in its own way:

| Attack | Modelled effect |
| --- | --- |
| Intercept-resend | $e_z$ and $e_x$ rise by $s/4$ |
| Detector blinding | Dark counts and double clicks fall to 5%, error rates fall to 70%, singles fall by a factor $1 - s/2$ |
| Trojan-horse probe | Back-reflection rises by $3s$, $e_x$ rises by $s/10$ |

The seven observed channels are the two error rates (binomial samples), the single, dark and double-click counts (Poisson samples), the back-reflection monitor, and the CHSH value $S = 2\sqrt{2}\,(1 - q_z - q_x)$ plus measurement noise.

### Detectors

All detectors are set to the same false-alarm budget on benign data.

- Static threshold (`static_threshold`): an alarm when $q_z + q_x$ exceeds its benign $(1 - \text{fa})$ quantile from the training days.
- Multi-monitor thresholds (`multi_threshold`): an alarm when any of four monitors crosses its own threshold, each set at a quarter of the budget: high error rate, low dark counts, low double clicks, high back-reflection.
- CUSUM (`cusum`): a one-sided cumulative sum on the error rate after removing a 10-minute rolling median. It is reported in the CSV file but not plotted.
- Classifier (`run`): a histogram gradient-boosting classifier on features built by `features`: rolling means over three windows, deviations from a 10-minute rolling median, ratios between channels, and rolling correlations between the error rate and dark counts. It is trained on three simulated days. The alarm threshold on its attack probability is set on a separate benign day, and it is tested on two further days.

## Multi-hop delivery: `src/deliver.py` and `src/pools.py`

### Outages

`outage_trace` makes each link alternate between up and down, with exponentially distributed durations of mean $\tau_{\text{up}}$ and $\tau_{\text{down}}$, in 1-second steps. The availability of a link is

$$A = \frac{\tau_{\text{up}}}{\tau_{\text{up}} + \tau_{\text{down}}} .$$

A key made on demand over $h$ hops needs every hop up at once, so the on-time probability of just-in-time delivery is $A^h$.

### Strategies

`simulate_path(hops, strategy)` returns the fraction of seconds in which a request for $d$ bits is served. $R$ is the key-mode rate of one hop.

| Strategy | A request is served when |
| --- | --- |
| `jit_trusted_relay` | every hop is up and $R \ge d$ |
| `jit_swap_no_memory` | every hop is up and the swapped rate without memory is at least $d$ |
| `jit_swap_memory` | every hop is up and the swapped rate with memory is at least $d$ |
| `pool_trusted_relay` | every hop's pool holds at least $d$ |
| `pool_end_to_end_swap` | the single end-to-end pool, filled at the swapped rate with memory while every hop is up, holds at least $d$ |
| `multipath_jit_k_of_n` | at least 2 of 3 disjoint paths are fully up |
| `multipath_pool_k_of_n` | at least 2 of 3 paths have every pool at or above $d$ |

A pool of capacity $C$ on a link with state $u_t \in \{0, 1\}$ evolves as

$$K_{t+1} = \min(C,\; K_t + R\,u_t) - d\,\mathbb{1}[\text{served}] .$$

### Entanglement swapping

Without memory (`swap_rate`), all $h$ links must deliver a pair in the same clock cycle:

$$R_{\text{swap}} = \nu\mu\,(\eta\,\eta_d)^h\, b^{\,h-1}\, f_s ,$$

with $f_s$ a flat secret fraction per swapped pair.

With memory (`swap_memory_model`), each link succeeds per clock cycle with probability $p = \mu\,\eta\,\eta_d$ and holds its pair until all links have one. The expected number of attempts is

$$N_h = \frac{H_h}{p}, \qquad H_h = \sum_{k=1}^{h} \frac1k ,$$

valid for small $p$. The waiting time is $t_w = N_h/\nu$. Stored pairs are depolarized with probability $q_m = 1 - e^{-t_w/T_2}$ for $h \ge 2$, and $q_m = 0$ for $h = 1$. A link pair of fidelity $F_\ell$ has Werner parameter $w_\ell = (4F_\ell - 1)/3$, and after the swaps the end-to-end pair has

$$w = \big(w_\ell\,(1 - q_m)\big)^h, \qquad F = \frac{3w + 1}{4} .$$

The key rate is

$$R_{\text{swap,mem}} = \frac{\nu}{N_h}\; b^{\,h-1}\; \eta_m^{\,2(h-1)}\; \max\!\big(0,\, 1 - H(p(F))\big),$$

where $p(F)$ are the Werner weights of the end-to-end pair. The factor $\eta_m^{2(h-1)}$ accounts for reading two stored halves at each of the $h-1$ intermediate nodes. The sources and assumptions behind these steps are recorded in the `formulas` section of `config.yaml`.

### Pool sizing

`pool_sim(h, rho, buf_s)` in `src/pools.py` uses a normalised supply rate $R = 1$. The demand is a fraction $\rho$ of the average supply, $d = \rho A R$, and the pool capacity is $C = B\,d$, where $B$ is the pool depth in seconds of demand. `pool_trace` returns the same simulation as a time series.

## One-to-many delivery: `src/multicast.py`

A hub is connected to $N$ receivers by links of equal length, each with independent outages. Let $\eta = \eta_f(L)\,\eta_d$ for one link and $R_b$ be the key-mode rate of one link.

A GHZ state shared by all receivers arrives at a rate that falls as the $N$-th power of the link transmission (`ghz_rate`):

$$R_{\text{GHZ}} = R_s\,\eta^N\,\eta_d\,f_G ,$$

where $f_G$ is a flat secret fraction and $R_s$ is the rate of the source. For an idealised deterministic source $R_s$ is a constant. For a source built from pair sources, $R_s = \nu\,\mu^{\lceil (N+1)/2 \rceil}$.

`on_time(N, strategy, demand)` returns the fraction of seconds in which the group key is delivered:

| Strategy | Delivered when |
| --- | --- |
| `bipartite_jit` | all $N$ links are up and $R_b \ge d$ |
| `ghz_jit` | all $N$ links are up and $R_{\text{GHZ}} \ge d$ |
| `bipartite_pools` | every receiver's pool holds at least $d$ |
| `bipartite_pools_receiver_fraction` | reported per receiver: the fraction of receivers whose pool holds at least $d$ |

Figure 11 compares GHZ and pairwise keys behind a shared bottleneck link with transmission $\eta_B$:

$$\text{ratio} = \frac{\nu\mu\,\eta_B\,\eta^N\,\eta_d\,f_G}{R_B / N},$$

where $R_B$ is the key-mode rate of the bottleneck, shared between $N$ receivers.

## Hybrid protocol and scheduling: `src/extend_net.py`

### Hybrid of QSDC and a key pool

`hybrid_link(L)` simulates one link with outages under three policies. Let $P$ be the verified pair rate, $k = R_K/P$ the key bits per pair and $s = R_D/P$ the superdense bits per pair, both from `rates_at`. The demand is $d = \varphi\,A\,P\,k$ and the pool capacity is $C = B\,d$.

| Policy | Each second |
| --- | --- |
| `key_pool` | If the link is up, add $P k$ to the pool. Serve from the pool if it holds at least $d$. |
| `qsdc_only` | Serve only if the link is up and $P s \ge d$. Nothing is stored. |
| `hybrid` | If the link is up and $P s \ge d$, serve by superdense coding using $d/s$ pairs, and add the key from the remaining $P - d/s$ pairs to the pool. Otherwise serve from the pool. |

The simulation also records the fraction of served traffic that used no key, the mean pool level, and the mean age of key when it is used, tracked first-in first-out.

The largest demand each policy can sustain follows from balancing supply and use. With a pool alone it is $A P k$. For the hybrid, the pool must cover the outages using the key made from spare pairs while the link is up, which gives

$$d_{\max}^{\text{hybrid}} = \frac{A P k}{(1 - A) + A\,k/s}, \qquad \text{gain} = \frac{d_{\max}^{\text{hybrid}}}{A P k} .$$

### Multicast scheduling

`schedule_sim(N, margin, buf_s, sched)` gives one source of rate $R = m N d / A$, where $m$ is the capacity margin, to $N$ receivers with their own pools and outages. Four ways of sharing the source are implemented: an equal fixed share, an equal share among receivers whose link is up, lowest pool first, and a share weighted by the inverse of the pool level.

## Finite-key effects: `src/extend_theory.py`

`finite_key_rate(n, Q)` returns the secret fraction for a block of $n$ pairs with error rate $Q$. A fraction $f_{pe}$ of the block is used for parameter estimation, leaving $n_k = n - n_{pe}$ pairs. The error rate is bounded by

$$Q_u = \min\!\Big(\tfrac12,\; Q + \sqrt{\frac{\ln(1/\varepsilon)}{2 n_{pe}}}\Big),$$

and the secret key length is

$$\ell = n_k\big(1 - h(Q_u) - f_{EC}\,h(Q)\big) - 2\log_2\frac{1}{\varepsilon} - 7\sqrt{n_k \log_2\frac{2}{\varepsilon}},$$

with $f_{EC}$ the error-correction efficiency. The function returns $\max(0, \ell/n)$, and zero for blocks below a minimum size.

`pool_vs_jit_blocks` compares two block sizes at each distance. Just-in-time delivery can use only the pairs that arrive within one deadline, $n = P\,t_{\text{deadline}}$. A pool can accumulate pairs for up to an hour, $n = \min(n_{\max},\, 3600\,P)$. The asymptotic rate is $P\,\max(0,\, 1 - h(Q) - f_{EC}\,h(Q))$.

`switch_threshold_qudit(d, F)` extends the switching rule to dimension $d$. For a state with weight $F$ on one generalised Bell state and the rest spread evenly over the other $d^2 - 1$, key mode gives $\log_2 d - H(p)$ and superdense mode gives $2\log_2 d - 2H(p)$, so the threshold is again $\tfrac12$.

## Design-space sweep: `src/sweep.py`

`build(mode)` lists every valid combination of six choices: distribution (direct, measurement-device-independent, heralded device-independent), certification, monitoring, transport, authentication and delivery. Combinations that cannot work together are left out, which leaves 804 designs.

Each design gets:

- the secure rate at two distances, from `rates_at`;
- the on-time probability at 4 hops, from the same delivery simulation as figure 7 (`on_time_table`). Transports with no key can only use just-in-time delivery and score zero with pooled delivery. Delivery with a post-quantum fallback is on time by construction;
- a security score, $1 - \tfrac18\sum_j x_j$, where $x_j \in [0, 1]$ is the exposure to each of eight attack classes: channel eavesdropping, detector side channels, Trojan-horse probing, source side channels, man-in-the-middle, relay compromise, key at rest, and fallback to computational security.

The exposure values are judgement scores, listed in `config.yaml` under `sweep.exposure`.

## Qiskit check: `src/qiskit_validation.py`

The module builds the Bell pair, the four superdense encodings with Bob's Bell measurement, the Z-basis and X-basis measurements, and the four CHSH settings as circuits, and runs them on the Aer simulator.

A Werner pair of fidelity $F$ is produced by depolarizing one half of a perfect pair with strength $\lambda = 4(1-F)/3$, since a depolarizing channel of strength $\lambda$ applies each Pauli error with probability $\lambda/4 = (1-F)/3$. Return-leg noise is a second depolarizing channel on the encoded qubit.

For the Bell test, Alice measures at angles $0$ and $\pi/2$ and Bob at $\pm\pi/4$ in the X-Z plane, and

$$S = E(0, \tfrac{\pi}{4}) + E(0, -\tfrac{\pi}{4}) + E(\tfrac{\pi}{2}, \tfrac{\pi}{4}) - E(\tfrac{\pi}{2}, -\tfrac{\pi}{4}) .$$

Each measured value is compared with its analytic value in units of the standard error expected from the number of shots: $\sqrt{p(1-p)/n}$ for a probability, and $\sqrt{\sum_i (1 - E_i^2)/n}$ for $S$.

## Figures and configuration: `src/figures.py` and `src/config.py`

`figures.py` has one function per figure or pair of figures. Each calls the modules above, writes a PNG file and a CSV file, and records headline numbers. `main` runs them in order and writes `results/key_numbers.json`.

`config.py` reads `config.yaml` once, checks it, and exposes the merged values as `CFG`. See the README for the layout of that file.
