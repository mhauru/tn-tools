# tn-tools

tn-tools is an assortment of miscellaneous tools and utilities that I use when
developing tensor network algorithms in Python3. Some of these are pretty
specific to my own uses, such as my favourite way of formatting log messages.
The ones most useful to others would be
* `datadispenser.py` (which uses `pact.py`), an automated disk-storage and
  retrieval system for data generated by algorithms. Meant to automate the
  process of "did I already run this algorithm with these parameters, and if I
  did, where did I store the output?"
* `ncon_sparseeig.py`, that implements sparse decomposition routines for tensor
  networks with an NCon-like syntax.

The level of documentation and code beauty varies. `datadispenser` is pretty
decent, `ncon_sparseeig` intimidates even me. The tools here rely on the
[abeliantensors](https://github.com/mhauru/abeliantensors) and
[ncon](https://github.com/mhauru/ncon) packages.

## Installation
```
pip install --user git+https://github.com/mhauru/tntools
```

## The files
`pact.py`
A module for storing data on the disk, such that each piece of data is uniquely
identified by a name for the type of data, and a dictionary of parameters. For
instance, the name could be "MERA_disentangler" and the parameters would be all
the parameters that went into producing this disentangler, such as the bond
dimension, the physical model it's used for and the optimization method. `pact`
can then store the data with the identifying information, and fetch the data
given the identifying information.

`datadispenser.py`
A module that generates data using various algorithms, and stores the data on
the disk (using `pact`). The idea is that a user just tells `datadispenser`
what kind of data she wants ("I want a MERA disentangler produced using these
parameters"), and `datadispenser` either finds the data already on disk, or
generates it for the user, storing it as well, in case it is requested later.
It also generates any prerequisite data necessary (such as the other tensors in
the same MERA).

`ncon_sparseeig.py`
A module that implements two user-facing functions: `ncon_sparseeig` and
`ncon_sparsesvd`. They provide a convenient interface, similar to that of the
`ncon` package, for doing eigenvalue and singular value decompositions of tensor
networks using power methods (from `scipy.sparse.linalg`), without ever
contracting the full network.

`multilineformatter.py`
A formatter class for the Python
[logging](https://docs.python.org/3/library/logging.html) module that formats
multiline messages nicely.

`logging_default.conf`
A default configuration for the Python logging module that for instance uses
the above `multilineformatter`.

`initialtensors.py`
A module that produces initial tensors for various lattice models in 2D and 3D,
that can be used to write down the partition function of the model. Used as
starting points for many tensor network algorithms.

`initialtensors_setup.py`
A module for interfacing `initialtensors.py` with `datadispenser`.

`modeldata.py`
A module that provides exact data for some solvable lattice models, such as
exact free energies and CFT data. Handy for benchmarking.

`yaml_config_parser.py`
A module for reading in parameters for various programs in the
[YAML](http://yaml.org/) format. Supports both `.yaml` files as configuration
files, and appending/overriding parameters using command line arguments.

