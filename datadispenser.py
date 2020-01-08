import importlib
import logging
import configparser
import numpy as np
import os
from . import multilineformatter
from .pact import Pact

""" Datadispenser is a module that can run various algorithms that take
different parameters and generate data, and store that data on the disk.
The goal is a user experience we one just tells datadispenser "I want
the data generated by algorithm X using parameters Y", and datadispenser
provides, either by getting from the disk or, if necessary, by running
the algorithm, possibly also generating (and storing) prerequisite data
in the process.

All pieces of data are labeled by two things: dataname and pars.
Dataname is a string, and pars is a dictionary, that holds all the
necessary parameters (with strings as keys) for the algorithm.

For an algorithm to work with datadispenser, pars should include a
parameter called "algorithm" with the name of the algorithm, for
instance "X". There should then be a python module called X_setup.py
that can be found by python's importlib, that provides the following
fields:

parinfo:
A dictionary, that has as its keys the possible parameters for the
algorithm in question. For each key, the value is another dictionary,
with two keys: "idfunc" and "default". "default" provides the default
value for this parameter, if none is specified in pars. "idfunc" is a
function that takes in two arguments, the dataname and the pars, and
returns a boolean for whether this parameter should be considered
an "ID parameter". If a parameter is an ID parameter, it means that all
data should be unique to the value of this parameter. For instance,
most crucial parameters of X would probably be ID parameters, but for
instance a parameter that only determines the verbosity of output
prints would not (we don't want to regenerate data just because we
happened to ask for a different amount of output this time).
Note that because idfunc is a function, whether something is an ID
parameter or no, can depend on the values of other parameters. (Think
of a case where some parameter turns some feature of the algorithm
off. If this is the case, then parameters related to this feature
should not be ID parameters when the feature is disabled.)

prereq_pairs:
prereq_pairs is a function that takes in the dataname and the pars.
It returns an iterable of pairs (tuples) of
(prereq_dataname, prereq_pars), where each pair specifies some piece
of data that is a prerequisite/input for generating the data for the
original dataname and pars.

generate:
generate is a function with the signature
generate(dataname, *args, pars=dict(), filelogger=None)
It generates the data requested by dataname and pars, and returns it
(in whatever format it finds suitable). *args will be populated
with all the data returned by calling generate on the prereq_pairs.
filelogges is a logger object for the python logging module, that writes
to a log file that will be stored with the data. Datadispenser
automatically sets up logging so that any calls to logging.info and
other similar functions will result in the output being written
to filelogger as well. However, the filelogger provided as an argument
for generate can be used to write additional things to this log file,
that do not for instance need to appear in stdout. In many cases
the filelogger argument can be ignored.

Optionally a setup module may also include the following fields:

version:
A version number for the algorithm. If this is provided, an additional
ID parameter called X_version (for algorithm called X) is created.

idpars_finalize
A function that takes in two arguments, pars and idpars. This can be
used to do final "postprocessing" to the ID parameters before they are
used for labeling the data that is generated and stored, or fetched.

A user of datadispenser would call the function get_data. It has the
following signature:
get_data(db, dataname, pars, return_pars=False, **kwargs)
The first argument is path to a database, i.e., a folder in which the
data is kept. return_pars specifies whether, with the data, the final
pars that has been updated with default values, is to be returned.
**kwargs can be used to provide values that override those in pars.

A user may also want to call the function
update_default_pars(dataname, pars, **kwargs)
which updates pars in-place to include the default values for all
the parameters for this piece of data that were not provided.

- - - 

Since we mostly use datadispenser with tensor network algorithms,
integration with the initialtensors.py and initialtensors_setup.py
modules is hardcoded.
"""


# A dictionary that maps each dataname to a function that takes in pars,
# and gives out the name of the setup module appropriate for this
# dataname and pars. Note that often the return value doesn't even
# depend on pars. If the dataname is not found in this dictionary,
# or the function returns None, then a default guess is made based on
# pars["algorithm"].
setupmodule_dict = {
    "ham": lambda pars: "tntools.initialtensors_setup",
    "A": lambda pars: (None if pars["iter_count"] > 0
                       else "tntools.initialtensors_setup"),
    "As": lambda pars: (None if pars["iter_count"] > 0
                        else "tntools.initialtensors_setup"),
    "A_impure": lambda pars: (None if pars["iter_count"] > 0
                              else "tntools.initialtensors_setup"),
    "As_impure": lambda pars: (None if pars["iter_count"] > 0
                               else "tntools.initialtensors_setup"),
    "As_impure111": lambda pars: (None if pars["iter_count"] > 0
                                  else "tntools.initialtensors_setup"),
    "As_impure333": lambda pars: (None if pars["iter_count"] > 0
                                  else "tntools.initialtensors_setup"),
    "T3D_spectrum": lambda pars: "T3D_spectrum" + "_setup",
    "T2D_spectrum": lambda pars: "T2D_spectrum" + "_setup",
}


# Always include a parameter called "store_data", that defaults to True.
parinfo = {
    "store_data": {
        "default": True,
    },
}


def apply_parinfo_defaults(pars, parinfo):
    for k, v in parinfo.items():
        if k not in pars:
            pars[k] = v["default"]
    return


def get_data(db, dataname, pars, return_pars=False, **kwargs):
    """ Get data from the disk if possible, if not, generate it. """
    pars = copy_update(pars, **kwargs)
    apply_parinfo_defaults(pars, parinfo)
    update_default_pars(dataname, pars)
    idpars = get_idpars(dataname, pars)
    p = Pact(db)
    if p.exists(dataname, idpars):
        data = p.fetch(dataname, idpars)
    else:
        data = generate_data(dataname, pars, db=db)
    retval = (data,)
    if return_pars:
        retval += (pars,)
    if len(retval) == 1:
        retval = retval[0]
    return retval


def copy_update(pars, **kwargs):
    pars = pars.copy()
    pars.update(kwargs)
    return pars


def update_default_pars(dataname, pars, **kwargs):
    """ Update pars, in-place, with the default values for this piece of
    data.
    """
    pars_copy = copy_update(pars, **kwargs)
    setupmod = get_setupmod(dataname, pars_copy)

    # Get the default for this setupmod, and update those in, since we
    # may need those to find the prereqs.
    parinfo = setupmod.parinfo
    apply_parinfo_defaults(pars_copy, parinfo)

    # Get the pars for the prereqs and update them in.
    prereq_pairs = setupmod.prereq_pairs(dataname, pars_copy)
    prereq_pars_all = dict()
    for prereq_name, prereq_pars in prereq_pairs:
        update_default_pars(prereq_name, prereq_pars)
        prereq_pars_all.update(prereq_pars)

    for k, v in prereq_pars_all.items():
        if k not in pars:
            pars[k] = v

    # Update the defaults for this module once more, now into pars, to
    # make sure that they override those coming from prerequisites.
    parinfo = setupmod.parinfo
    apply_parinfo_defaults(pars, parinfo)
    return pars


def get_idpars(dataname, pars):
    setupmod = get_setupmod(dataname, pars)
    idpars = dict()

    # Get the idpars for the prereqs and update them in.
    prereq_pairs = setupmod.prereq_pairs(dataname, pars)
    for prereq_name, prereq_pars in prereq_pairs:
        prereq_idpars = get_idpars(prereq_name, prereq_pars)
        idpars.update(prereq_idpars)

    # Get the idpars for this setupmod, and update those in.
    parinfo = setupmod.parinfo
    for k, v in parinfo.items():
        if v["idfunc"](dataname, pars):
            idpars[k] = pars[k]
    if hasattr(setupmod, "version"):
        modulename = get_setupmod_name(dataname, pars)
        idpars[modulename + "_version"] = setupmod.version
    if hasattr(setupmod, "idpars_finalize"):
        idpars = setupmod.idpars_finalize(pars, idpars)
    return idpars


def generate_data(dataname, pars, db=None):
    havedb = True if db is not None else False
    storedata = pars["store_data"] and havedb
    if havedb:
        p = Pact(db)
    if storedata:
        idpars = get_idpars(dataname, pars)
    setupmod = get_setupmod(dataname, pars)
    prereq_pairs = setupmod.prereq_pairs(dataname, pars)
    prereqs = []
    for prereq_name, prereq_pars in prereq_pairs:
        if havedb:
            prereq = get_data(db, prereq_name, prereq_pars)
        else:
            prereq = generate_data(prereq_name, prereq_pars)
        prereqs.append(prereq)

    if storedata:
        handler, filelogger = set_logging_handlers(p, dataname, pars)
    else:
        filelogger = None
    data = setupmod.generate(dataname, *prereqs, pars=pars,
                             filelogger=filelogger)
    if storedata:
        remove_logging_handlers(logging.getLogger(), handler)
        remove_logging_handlers(filelogger, handler)

    if storedata:
        p.store(data, dataname, idpars)
    return data


def get_setupmod_name(dataname, pars):
    modulename = (None if dataname not in setupmodule_dict
                  else setupmodule_dict[dataname](pars))
    if modulename is None:
        algoname = pars["algorithm"]
        modulename =  "{}_setup".format(algoname, algoname)
        try:
            if importlib.util.find_spec(modulename) is None:
                modulename = "{}.{}".format(algoname, modulename)
        except AttributeError:
            if importlib.find_loader(modulename) is None:
                modulename = "{}.{}".format(algoname, modulename)
    return modulename


def get_setupmod(dataname, pars):
    modulename = get_setupmod_name(dataname, pars)
    setupmod = importlib.import_module(modulename)
    return setupmod


def set_logging_handlers(p, dataname, pars):
    rootlogger = logging.getLogger()
    filelogger = logging.getLogger("datadispenser_file")
    filelogger.propagate = False

    idpars = get_idpars(dataname, pars)
    logfilename = p.generate_path(dataname, idpars, extension=".log")
    os.makedirs(os.path.dirname(logfilename), exist_ok=True)
    filehandler = logging.FileHandler(logfilename, mode='w')
    if "debug" in pars and pars["debug"]:
        filehandler.setLevel(logging.DEBUG)
    else:
        filehandler.setLevel(logging.INFO)

    parser = configparser.ConfigParser(interpolation=None)
    tools_path = os.path.dirname(multilineformatter.__file__)
    parser.read(tools_path + '/logging_default.conf')
    fmt = parser.get('formatter_default', 'format')
    datefmt = parser.get('formatter_default', 'datefmt')
    formatter = multilineformatter.MultilineFormatter(fmt=fmt, datefmt=datefmt)

    filehandler.setFormatter(formatter)
    rootlogger.addHandler(filehandler)
    filelogger.addHandler(filehandler)
    return filehandler, filelogger


def remove_logging_handlers(logger, *args):
    for l in args:
        l.close()
        logger.removeHandler(l)


