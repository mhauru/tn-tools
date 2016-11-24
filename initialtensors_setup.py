import numpy as np
import initialtensors
import toolbox

twodee_models = {"ising", "potts3", "sixvertex"}
threedee_models = {"ising3d"}

parinfo = {
    # Generic parameters
    "model": {
        "default": "",
        "idfunc":  lambda pars: True
    },
    "dtype": {
        "default": np.float_,
        "idfunc":  lambda pars: True
    },
    "initial2x2": {
        "default": False,
        "idfunc":  lambda pars: pars["model"] in twodee_models
    },
    "initial4x4": {
        "default": False,
        "idfunc":  lambda pars: pars["model"] in twodee_models
    },
    "initial2x2x2": {
        "default": False,
        "idfunc":  lambda pars: pars["model"] in threedee_models
    },
    "symmetry_tensors": {
        "default": False,
        "idfunc":  lambda pars: True
    },

    # Model dependent parameters.
    # Ising and 3-state Potts
    "beta": {
        "default": 1.,
        "idfunc":  lambda pars: pars["model"] in {"ising", "potts3"}
    },

    "J": {
        "default": 1.,
        "idfunc":  lambda pars: pars["model"] in {"ising", "potts3"}
    },
    "H": {
        "default": 0.,
        "idfunc":  lambda pars: pars["model"] == "ising"
    },

    # Sixvertex model
    "sixvertex_a": {
        "default": 1.,
        "idfunc":  lambda pars: pars["model"] == "sixvertex"
    },
    "sixvertex_b": {
        "default": 1.,
        "idfunc":  lambda pars: pars["model"] == "sixvertex"
    },
    "sixvertex_c": {
        "default": np.sqrt(2),
        "idfunc":  lambda pars: pars["model"] == "sixvertex"
    },
}


def prereq_pairs(dataname, pars):
    if dataname in {"A", "As"}:
        res = []
    else:
        raise ValueError("Unknown dataname: {}".format(dataname))
    return res


def generate(dataname, *args, pars=dict(), filelogger=None):
    if dataname in {"A", "As"}:
        A = initialtensors.get_initial_tensor(pars)
        log_fact = 0
        if pars["initial4x4"]:
            A = toolbox.contract2x2(A)
            A = toolbox.contract2x2(A)
        elif pars["initial2x2"]:
            A = toolbox.contract2x2(A)
    else:
        raise ValueError("Unknown dataname: {}".format(dataname))
    res = (A, log_fact) if dataname == "A" else ((A,)*8, log_fact)
    return res
