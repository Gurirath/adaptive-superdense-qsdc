# Secure quantum communication with entanglement-based key sharing and superdense coding

Gurirath Singh Khurana · simulation study · October 2026

The question:
1. Two ways to send secrets with entangled photon pairs: key mode (make a secret key, then encrypt) and superdense mode (send the message itself, 2 bits per qubit).
2. Which is more secure and efficient, when should each be used, and how do we stop keys arriving late over many hops and to many receivers?

What we built:
1. A density-matrix model of superdense coding and entanglement-based key distribution (Python, NumPy).
2. Fiber-link simulations from 0 to 250 km with realistic detectors, noise and quantum memory.
3. A machine-learning attack detector on simulated link telemetry.
4. Network simulations of outages over multiple hops and 1-to-N multicast.
5. A sweep of all 804 valid combinations of source, security check, monitoring, transport, authentication and delivery.

Main results:
1. Superdense coding gives 2× the secure bits of key mode for every verified pair (1.27 vs 0.63 bits at 95% fidelity). Eve learns at most H(p), the noise entropy of the pair, even if she steals the travelling qubit (fig02).
2. Switching rule: use superdense mode only when more than half the photons survive the return trip (η > 0.5). This holds for any noise level and any qudit dimension (fig03).
3. In practice that means superdense wins only on short links: about 6 km today, 14 km at most with a perfect memory, never with a standard linear-optics Bell measurement (fig01, fig04).
4. The ping-pong protocol is never secure with real detectors (0.85 efficiency), because the round trip already falls below the 75% security bound.
5. ML detection caught 99% of attacks vs 27% for the standard error-rate threshold, at a 1% false-alarm budget, including detector blinding and Trojan horse attacks that the standard check misses (fig05, fig06).
6. Keys arrive late over many hops because every hop must work at the same moment: on-time delivery falls as 0.909^hops, to 38% at 10 hops (fig07).
7. Fix: a key pool at every hop. A pool holding about 4× the average outage restores 94–100% on-time delivery even at 8 hops and 95% load (fig08, fig09).
8. Pools also let you use larger finite-key blocks: 1.8× more key at 100 km, and key keeps flowing at 150–200 km where 1-second blocks give zero (fig14).
9. Superdense mode cannot use pools because it has no key to store. Buffering entanglement through outages needs about 1,000 s of quantum memory coherence (fig15).
10. Multicast to N receivers: per-receiver pools keep 94% all-receivers-on-time at N = 32, vs 4.6% without pools. GHZ conference keys fail beyond about 4–6 receivers (fig10).
11. GHZ only beats separate links (up to 1.8×) behind a bottleneck with receivers within about 2 km (fig11).
12. For multicast, buffer depth matters, not source capacity: buffer 10 → 120 s lifts on-time 40% → 97%, while 45% more source power adds about 2 points (fig16).

Proposed method (QSDC + key-pool hybrid):
1. Check every block of pairs first (3-basis tests plus ML monitoring).
2. While the link is up, send messages directly by superdense coding: no key ever exists for them.
3. Spare pairs fill a key pool; during outages, messages use one-time-pad keys from the pool.
4. Result on a 1 km link: 99.6% on-time (same as pools alone), 92% of traffic never touches a stored key, and 20% more capacity (fig12, fig13).
5. Trade-off: stored keys wait longer before use (204 s vs 86 s), so key expiry should be added.

What looks new (not found in our literature search):
1. The closed-form switching rule between key mode and superdense mode.
2. Showing that QSDC's "no key" property is exactly what makes it fail under outages.
3. The QSDC + key-pool hybrid design.
4. Outage-based pool sizing and the finite-key benefit of pools.

Already known (we reproduced it): the 2× secure dense coding rate, ping-pong's weakness under loss, GHZ advantage only in bottleneck networks.

Limits: all results are simulations under stated assumptions (0.2 dB/km fiber, 0.85 detectors, outages averaging 300 s up / 30 s down). Attack signatures for the ML detector are modelled, not measured. Next steps: finite-key security proof of the switch, and testing the detector on real hardware data.
