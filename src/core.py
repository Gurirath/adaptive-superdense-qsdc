import numpy as np
from functools import reduce

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
Y = 1j * X @ Z
PAULIS = [I2, X, Z, X @ Z]


def kron(*ops):
    return reduce(np.kron, ops)


def ket(bits):
    v = np.zeros(2 ** len(bits), dtype=complex)
    v[int("".join(str(b) for b in bits), 2)] = 1
    return v


PHI_P = (ket([0, 0]) + ket([1, 1])) / np.sqrt(2)
BELL = [kron(P, I2) @ PHI_P for P in PAULIS]


def h2(x):
    x = np.clip(x, 1e-15, 1 - 1e-15)
    return float(-x * np.log2(x) - (1 - x) * np.log2(1 - x))


def shannon(p):
    p = np.asarray(p, dtype=float)
    p = p[p > 1e-15]
    return float(-(p * np.log2(p)).sum())


def vn_entropy(rho):
    w = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    w = w[w > 1e-12]
    return float(-(w * np.log2(w)).sum())


def ptrace(rho, dims, keep):
    n = len(dims)
    rho = rho.reshape(dims + dims)
    trace_out = [i for i in range(n) if i not in keep]
    idx = list(range(2 * n))
    for t in sorted(trace_out, reverse=True):
        rho = np.trace(rho, axis1=t, axis2=t + rho.ndim // 2)
    d = int(np.prod([dims[k] for k in keep]))
    return rho.reshape(d, d)


def werner_weights(F):
    r = (1 - F) / 3
    return np.array([F, r, r, r])


def bell_diag_purification(p):
    psi = np.zeros(4 * 4, dtype=complex)
    for i, pi in enumerate(p):
        e = np.zeros(4, dtype=complex)
        e[i] = 1
        psi += np.sqrt(pi) * np.kron(BELL[i], e)
    return psi


def depolarizing_kraus(q):
    return [np.sqrt(1 - 3 * q / 4) * I2, np.sqrt(q / 4) * X, np.sqrt(q / 4) * Y, np.sqrt(q / 4) * Z]


def stinespring(kraus):
    d_env = len(kraus)
    V = np.zeros((2 * d_env, 2), dtype=complex)
    for k, K in enumerate(kraus):
        e = np.zeros(d_env, dtype=complex)
        e[k] = 1
        V += np.kron(K, e.reshape(-1, 1))
    return V


def sdc_information(p, q_leg2):
    psi = bell_diag_purification(p)
    V = stinespring(depolarizing_kraus(q_leg2))
    rhos_bob, rhos_eve_pass, rhos_eve_intercept = [], [], []
    for P in PAULIS:
        enc = kron(P, I2, np.eye(4)) @ psi
        rho_intercept = np.outer(enc, enc.conj())
        rhos_eve_intercept.append(ptrace(rho_intercept, [2, 2, 4], [0, 2]))
        full = np.kron(V, np.eye(8)) @ enc
        full = full.reshape(2, 4, 2, 4).transpose(0, 2, 3, 1).reshape(-1)
        rho = np.outer(full, full.conj())
        dims = [2, 2, 4, 4]
        rhos_bob.append(ptrace(rho, dims, [0, 1]))
        rhos_eve_pass.append(ptrace(rho, dims, [2, 3]))

    def holevo(rhos):
        avg = sum(rhos) / len(rhos)
        return vn_entropy(avg) - np.mean([vn_entropy(r) for r in rhos])

    P_bob = np.array([[np.real(BELL[j].conj() @ rb @ BELL[j]) for j in range(4)] for rb in rhos_bob])
    joint = P_bob / 4
    I_ab = shannon(joint.sum(1)) + shannon(joint.sum(0)) - shannon(joint.ravel())
    return {
        "I_bob": I_ab,
        "chi_eve_passive": holevo(rhos_eve_pass),
        "chi_eve_intercept": holevo(rhos_eve_intercept),
        "secrecy_per_pair": max(0.0, I_ab - holevo(rhos_eve_pass)),
    }


def sdc_linear_optics(p, q_leg2=0.0):
    symbols = [0, 1, 3]
    partition = [[0, 2], [1], [3]]
    qv = np.array([1 - 3 * q_leg2 / 4, q_leg2 / 4, q_leg2 / 4, q_leg2 / 4])
    klein = np.array([[0, 1, 2, 3], [1, 0, 3, 2], [2, 3, 0, 1], [3, 2, 1, 0]])
    pp = np.zeros(4)
    for i in range(4):
        for j in range(4):
            pp[klein[i, j]] += p[i] * qv[j]
    joint = np.zeros((3, 3))
    for a, k in enumerate(symbols):
        for b, cls in enumerate(partition):
            joint[a, b] = sum(pp[e] for e in range(4) if klein[k, e] in cls) / 3
    I_ab = shannon(joint.sum(1)) + shannon(joint.sum(0)) - shannon(joint.ravel())
    psi = bell_diag_purification(p)
    rhos = []
    for k in symbols:
        enc = kron(PAULIS[k], I2, np.eye(4)) @ psi
        rhos.append(ptrace(np.outer(enc, enc.conj()), [2, 2, 4], [0, 2]))
    avg = sum(rhos) / 3
    chi = vn_entropy(avg) - np.mean([vn_entropy(r) for r in rhos])
    return I_ab, chi


def sdc_secrecy_closed_form(p, q_leg2):
    qv = np.array([1 - 3 * q_leg2 / 4, q_leg2 / 4, q_leg2 / 4, q_leg2 / 4])
    klein = np.array([[0, 1, 2, 3], [1, 0, 3, 2], [2, 3, 0, 1], [3, 2, 1, 0]])
    pp = np.zeros(4)
    for i in range(4):
        for j in range(4):
            pp[klein[i, j]] += p[i] * qv[j]
    return 2 - shannon(pp), shannon(pp) - shannon(qv) + shannon(qv), pp


def qber_from_weights(p):
    return float(p[1] + p[3]), float(p[2] + p[3])


def chsh_from_weights(p):
    return float(np.sqrt(2) * (abs(p[0] - p[1] - p[2] + p[3]) + abs(p[0] + p[1] - p[2] - p[3])))


def key_rate_bbm92(p):
    ez, ex = qber_from_weights(p)
    return max(0.0, 1 - h2(ex) - h2(ez))


def key_rate_tomographic(p):
    return max(0.0, 1 - shannon(p))


def key_rate_di(S, Q):
    if S <= 2:
        return 0.0
    arg = (1 + np.sqrt(max(0.0, (S / 2) ** 2 - 1))) / 2
    return max(0.0, 1 - h2(Q) - h2(arg))


def finite_key_penalty(n, eps=1e-10):
    if n <= 0:
        return 1.0
    return 7 * np.sqrt(np.log2(2 / eps) / n)
