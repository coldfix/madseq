Changelog
~~~~~~~~~

0.4.1
=====

- use different names for slices
- fix sequence name in comment before templates


0.4.0
=====

- add 'use_at' slicing option that enables to use AT values


0.3.2
=====

- internal: remove attribute access for Element properties
- fix bugged Element.copy and .__contains__ regarding to base elements
- fix JSON/YAML serialization errors
- fix bugged implementation for predefined elements
- fix bugged LOOP style
- fix bugged makethin
- fix bugged use_optics
- rename 'use_optics' => 'template'. technically, this is a change in the
  public interface, but  we are still in 0.X and furthermore the feature was
  not working before anyway.


0.3.1
=====

- use `semantic versioning <http://semver.org/>`
- fix deep attribute lookup for elements


0.3
===

- redesigned command line
- fix erroneous parsing of MAD-X arrays, like KNL={...}
- remove inline attributes for slicing
- extended slicing via slicing configuration file
- fix usability of template (predefined) elements
