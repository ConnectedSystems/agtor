Agtor
=====

An agricultural water management model currently under development.


Description
===========
Based on an earlier version developed for the Lower Campaspe region in North-Central Victoria.

Agtor is designed to facilitate inter-disciplinary investigation of interactions across domains and scales involving agriculture.

Contributions are welcome.

Why the name "Agtor"?
------------

The model represents agricultural actors within a system and so the name is a portmandeau of "agriculture" and "actor".


Development Setup
=================

1. Fork or clone this repository.
2. Set up and activate a conda environment for the project (optional but recommended).
3. Disable pyscaffold within the `setup.py` file

   i.e. change `setup(use_pyscaffold=True)` to `setup(use_pyscaffold=False)`

4. Within the project folder, run `pip install -e .` or `python setup.py develop`

   After the install completes, discard/revert the change to `setup.py` -
   i.e. `setup(use_pyscaffold=False)` to `setup(use_pyscaffold=True)`

The tests found in the `tests` directory represent tentative usage examples. The `test_run.py` file gives an example of a model run.

Run from the top-level of the project, e.g.

```bash
$ python ./tests/test_run.py
```

As Agtor is under development all current details are subject to change.


Note
====

This project has been set up using PyScaffold 3.2.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
