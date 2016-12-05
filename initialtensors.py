import numpy as np
from scon import scon
from tensors.tensor import Tensor
from tensors.symmetrytensors import TensorZ2, TensorZ3, TensorU1

""" Module for getting the initial tensors for different models. """

def ising_hamiltonian(pars):
    ham = (- pars["J"]*np.array([[ 1,-1],
                                 [-1, 1]],
                                dtype=pars["dtype"])
           + pars["H"]*np.array([[-1, 0],
                                 [ 0, 1]],
                                dtype=pars["dtype"]))
    return ham

def potts3_hamiltonian(pars):
    ham = -pars["J"]*np.eye(3, dtype=pars["dtype"])
    return ham

hamiltonians = {}
hamiltonians["ising"] = ising_hamiltonian
hamiltonians["potts3"] = potts3_hamiltonian

symmetry_classes_dims_qims = {}
symmetry_classes_dims_qims["ising"] = (TensorZ2, [1,1], [0,1])
symmetry_classes_dims_qims["potts3"] = (TensorZ3, [1,1,1], [0,1,2])

# Transformation matrices to the bases where the symmetry is explicit.
symmetry_bases = {}
symmetry_bases["ising"] = np.array([[1, 1],
                                    [1,-1]]) / np.sqrt(2)
phase = np.exp(2j*np.pi/3)
symmetry_bases["potts3"] = np.array([[1,       1,         1],
                                     [1,    phase, phase**2],
                                     [1, phase**2,    phase]],
                                    dtype=np.complex_) / np.sqrt(3)
del(phase)

def get_initial_tensor(pars, **kwargs):
    if kwargs:
        pars = pars.copy()
        pars.update(kwargs)
    model_name = pars["model"].strip().lower()
    if model_name == "sixvertex":
        return get_initial_sixvertex_tensor(pars)
    elif model_name == "ising3d":
        return get_initial_tensor_ising_3d(pars)
    ham = hamiltonians[model_name](pars)
    boltz = np.exp(-pars["beta"]*ham)
    T_0 = np.einsum('ab,bc,cd,da->abcd', boltz, boltz, boltz, boltz)
    u = symmetry_bases[model_name]
    u_dg = u.T.conjugate()
    T_0 = scon((T_0, u, u, u_dg, u_dg),
               ([1,2,3,4], [-1,1], [-2,2], [3,-3], [4,-4]))
    if pars["symmetry_tensors"]:
        cls, dim, qim = symmetry_classes_dims_qims[model_name]
        T_0 = cls.from_ndarray(T_0, shape=[dim]*4, qhape=[qim]*4,
                               dirs=[1,1,-1,-1])
    else:
        T_0 = Tensor.from_ndarray(T_0)
    return T_0


def get_initial_sixvertex_tensor(pars):
    try:
        a = pars["sixvertex_a"]
        b = pars["sixvertex_b"]
        c = pars["sixvertex_c"]
    except KeyError:
        u = pars["sixvertex_u"]
        lmbd = pars["sixvertex_lambda"]
        rho = pars["sixvertex_rho"]
        a = rho*np.sin(lmbd - u)
        b = rho*np.sin(u)
        c = rho*np.sin(lmbd)
    T_0 = np.zeros((2,2,2,2), dtype=pars["dtype"])
    T_0[1,0,0,1] = a
    T_0[0,1,1,0] = a
    T_0[0,0,1,1] = b
    T_0[1,1,0,0] = b
    T_0[0,1,0,1] = c
    T_0[1,0,1,0] = c
    if pars["symmetry_tensors"]:
        dim = [1,1]
        qim = [-1,1]
        T_0 = TensorU1.from_ndarray(T_0, shape=[dim]*4, qhape=[qim]*4,
                                    dirs=[1,1,1,1])
        T_0 = T_0.flip_dir(2)
        T_0 = T_0.flip_dir(3)
    else:
        T_0 = Tensor.from_ndarray(T_0)
    return T_0


def get_KW_tensor(pars):
    eye = np.eye(2, dtype=np.complex_)
    ham = hamiltonians["ising"](pars)
    B = np.exp(-pars["beta"] * ham)
    H = np.array([[1,1], [1,-1]], dtype=np.complex_)/np.sqrt(2)
    y_trigged = np.ndarray((2,2,2), dtype=np.complex_)
    y_trigged[:,:,0] = eye
    y_trigged[:,:,1] = sigma('y')
    D_sigma = np.sqrt(2) * np.einsum('ab,abi,ic,ad,adk,kc->abcd',
                                     B, y_trigged, H,
                                     B, y_trigged.conjugate(), H)

    u = symmetry_bases["ising"]
    u_dg = u.T.conjugate()
    D_sigma = scon((D_sigma, u, u, u_dg, u_dg),
                   ([1,2,3,4], [-1,1], [-2,2], [3,-3], [4,-4]))
    if pars["symmetry_tensors"]:
        D_sigma = TensorZ2.from_ndarray(D_sigma, shape=[[1,1]]*4,
                                        qhape=[[0,1]]*4, dirs=[1,1,-1,-1])
    else:
        D_sigma = Tensor.from_ndarray(D_sigma, dirs=[1,1,-1,-1])
    return D_sigma


def get_KW_unitary(pars):
    eye = np.eye(2, dtype=np.complex_)
    CZ = Csigma_np("z")
    U = scon((CZ,
              R(np.pi/4, 'z'), R(np.pi/4, 'x'),
              R(np.pi/4, 'y')),
             ([-1,-2,5,6],
              [-3,5], [3,6],
              [-4,3]))
    u = symmetry_bases["ising"]
    u_dg = u.T.conjugate()
    U = scon((U, u, u_dg, u_dg, u),
             ([1,2,3,4], [-1,1], [-2,2], [3,-3], [4,-4]))
    U *= -1j
    if pars["symmetry_tensors"]:
        U = TensorZ2.from_ndarray(U, shape=[[1,1]]*4, qhape=[[0,1]]*4,
                                  dirs=[1,1,-1,-1])
    else:
        U = Tensor.from_ndarray(U, dirs=[1,1,1,-1,-1,-1])
    return U


def Csigma_np(sigma_str):
    eye = np.eye(2, dtype=np.complex_)
    CNOT = np.zeros((2,2,2,2), dtype=np.complex_)
    CNOT[:,0,:,0] = eye
    CNOT[:,1,:,1] = sigma(sigma_str)
    return CNOT


def sigma(c):
    if c=="x":
        res = np.array([[ 0, 1],
                        [ 1, 0]], dtype=np.complex_)
    elif c=="y":
        res = np.array([[ 0j,-1j],
                        [ 1j, 0j]], dtype=np.complex_)
    elif c=="z":
        res = np.array([[ 1, 0],
                        [ 0,-1]], dtype=np.complex_)
    return res


def R(alpha, c):
    s = sigma(c)
    eye = np.eye(2, dtype=np.complex_)
    res = np.cos(alpha)*eye + 1j*np.sin(alpha)*s
    return res

# # # # # # # # # # # # # 3D stuff # # # # # # # # # # # # # # # # #
# TODO: Incorporate this into the more general framework.
# TODO: Implement this for symmetry preserving tensors.

def get_initial_tensor_CDL_3d(pars):
    delta = np.eye(2, dtype = pars["dtype"])
    T = np.einsum(('ae,fi,jm,nb,cq,rk,lu,vd,gs,to,pw,xh '
                   '-> abcdefghijklmnopqrstuvwx'),
                  delta, delta, delta, delta, delta, delta,
                  delta, delta, delta, delta, delta, delta)
    return Tensor.from_ndarray(T.reshape((16,16,16,16,16,16)))


def get_initial_tensor_CDL_3d_v2(pars):
    delta = np.eye(2, dtype = pars["dtype"])
    T = scon((delta,)*12,
             ([-11,-21], [-12,-41], [-13,-51], [-14,-61],
              [-31,-22], [-32,-42], [-33,-52], [-34,-62],
              [-23,-63], [-64,-43], [-44,-53], [-54,-24]))
    return Tensor.from_ndarray(T.reshape((16,16,16,16,16,16)))


def get_initial_tensor_CQL_3d(pars):
    delta = np.array([[[1,0],[0,0]],[[0,0],[0,1]]])
    T = np.einsum(('aeu,fiv,gjq,hbr,mcw,nxk,ols,ptd '
                   '-> abcdefghijklmnopqrstuvwx'),
                  delta, delta, delta, delta, delta, delta, delta,
                  delta)
    return Tensor.from_ndarray(T.reshape((16,16,16,16,16,16)))

# DEBUG
#global_random_T_0 = TensorZ2.random(shape=[[1,1]]*6, dirs=[1,1,-1,-1,1,-1])
# END DEBUG

def get_initial_tensor_ising_3d(pars):
    beta = pars["beta"]
    ham = ising3d_ham(beta)
    T_0 = np.einsum('ai,aj,ak,al,am,an -> ijklmn',
                    ham, ham, ham, ham, ham, ham)
    if pars["symmetry_tensors"]:
        cls, dim, qim = TensorZ2, [1,1], [0,1]
        T_0 = cls.from_ndarray(T_0, shape=[dim]*6, qhape=[qim]*6,
                               dirs=[1,1,-1,-1,1,-1])
    else:
        T_0 = Tensor.from_ndarray(T_0)
    # DEBUG
    #T_0 = global_random_T_0
    # END DEBUG
    return T_0


# # # # # # # # # # # # # # # # Impurities # # # # # # # # # # # # # # # #


impurity_dict = dict()
# Ising
ising_dict = {
    "id": np.eye(2),
    "sigmax": np.real(sigma("x")),
    "sigmay": sigma("y"),
    "sigmaz": np.real(sigma("z"))
}
for k, M in ising_dict.items():
    u = symmetry_bases["ising"]
    u_dg = u.T.conjugate()
    M = scon((M, u, u_dg),
             ([1,2], [-1,1], [-2,2]))
    cls, dim, qim = symmetry_classes_dims_qims["ising"]
    M = cls.from_ndarray(M, shape=[dim]*2, qhape=[qim]*2,
                         dirs=[1,-1])
    ising_dict[k] = lambda pars: M
impurity_dict["ising"] = ising_dict
del(ising_dict)

impurity_dict["ising3d"] = dict()
impurity_dict["ising3d"]["id"] = lambda pars: TensorZ2.eye([1,1])
impurity_dict["ising3d"]["sigmaz"] = lambda pars: (
    TensorZ2.from_ndarray(sigmaz("z"), shape=[[1,1]]*2, qhape=[[0,1]]*2,
                          dirs=[1,-1])
)
impurity_dict["ising3d"]["sigmax"] = lambda pars: (
    TensorZ2.from_ndarray(sigmaz("x"), shape=[[1,1]]*2, qhape=[[0,1]]*2,
                          dirs=[1,-1])
)
impurity_dict["ising3d"]["sigmay"] = lambda pars: (
    TensorZ2.from_ndarray(sigmaz("y"), shape=[[1,1]]*2, qhape=[[0,1]]*2,
                          dirs=[1,-1])
)

def ising3d_ham(beta):
    res = np.array([[np.cosh(beta)**0.5,  np.sinh(beta)**0.5],
                    [np.cosh(beta)**0.5, -np.sinh(beta)**0.5]])
    return res

def ising3d_ham_inv(beta):
    res = 0.5*np.array([[np.cosh(beta)**(-0.5),  np.cosh(beta)**(-0.5)],
                        [np.sinh(beta)**(-0.5), -np.sinh(beta)**(-0.5)]])
    return res

def ising3d_ham_T(beta):
    res = np.array([[np.cosh(beta)**0.5,  np.cosh(beta)**0.5],
                    [np.sinh(beta)**0.5, -np.sinh(beta)**0.5]])
    return res

def ising3d_ham_T_inv(beta):
    res = 0.5*np.array([[np.cosh(beta)**(-0.5),  np.sinh(beta)**(-0.5)],
                        [np.cosh(beta)**(-0.5), -np.sinh(beta)**(-0.5)]])
    return res

def ising3d_U(beta):
    matrix = (ising3d_ham_inv(beta)
              .dot(sigma("z"))
              .dot(ising3d_ham(beta))
              .dot(ising3d_ham_T(beta))
              .dot(sigma("z"))
              .dot(ising3d_ham_T_inv(beta)))
    matrix = np.real(matrix)
    matrix = TensorZ2.from_ndarray(matrix, shape=[[1,1]]*2, qhape=[[0,1]]*2,
                                   dirs=[-1,1])
    # Factor of -1 because U = - \partial log Z / \partial beta, and a
    # factor of 3 because there are two bonds per lattice site, and we
    # normalize by number of sites.
    matrix *= -3
    return matrix

impurity_dict["ising3d"]["U"] = lambda pars: ising3d_U(pars["beta"])


def get_initial_impurity(pars, **kwargs):
    if kwargs:
        pars = pars.copy()
        pars.update(kwargs)
    A_pure = get_initial_tensor(pars)
    model = pars["model"]
    impurity = pars["impurity"]
    try:
        impurity_matrix = impurity_dict[model][impurity](pars)
    except KeyError:
        msg = ("Unknown (model, impurity) combination: ({}, {})"
               .format(model, impurity))
        raise ValueError(msg)
    # TODO The expectation that everything is in the symmetry basis
    # clashes with how ising and potts initial tensors are generated.
    if not pars["symmetry_tensors"]:
        impurity_matrix = Tensor.from_ndarray(impurity_matrix.to_ndarray())
    A_indices = [-i for i in range(1, len(A_pure.shape)+1)]
    A_indices[0] *= -1
    A_impure = scon((A_pure, impurity_matrix), (A_indices, [1,-1]))
    return A_impure

