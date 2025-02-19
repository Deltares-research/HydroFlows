.. _method_library:

Method library
==============


Flood risk workflows
--------------------

# add workflow diagram here



Table overview with methods

.. list-table:: Table overview with methods
    :header-rows: 1
    :widths: 20 15 40 10 30

    * -
      - build / get
      - update model
      - run
      - postprocess
    * - Coastal data
      -
      -
      - N.A.
      -
    * - Rainfall data
      -
      -
      -
      -
    * - SFINCS (flood hazard)
      - :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild`; :py:class:`~hydroflows.methods.sfincs.sfincs_region.SfincsRegion`
      - update forcing
      -
      - validation; downscale; postprocess
    * - Wflow (discharge boundary)
      -
      - update forcing; update climate scaling factors
      -
      - discharge design events
    * - Delft-FAIT (impact)
      -
      -
      -
      -
    * - FloodAdapt
      -
      -
      -
      -
