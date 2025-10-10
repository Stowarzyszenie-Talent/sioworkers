{ pkgs
, stdenv
, lib
, buildPythonPackage
, pythonAtLeast
, pythonOlder

, six
, filetracker
, simplejson
, twisted
, urllib3
, sortedcontainers
, berkeleydb
, supervisor

, pytest
, pytest-timeout

, ...
}:

buildPythonPackage {
  pname = "sioworkers";
  version = "1.0";
  disabled = pythonAtLeast "3.13" || pythonOlder "3.9";

  src = builtins.path {
    path = ./..;
    filter = path: type: builtins.match ".*/nix" path == null;
  };

  doCheck = false;
  NO_JAVA_TESTS = "1";
  #TEST_SANDBOXES = "1"; # These are broken anyway, `supervisor` moment.
  # Doesn't set correctly without this for some reason.
  LOCALE_ARCHIVE = "${pkgs.glibcLocales}/lib/locale/locale-archive";

  # Only for tests
  nativeBuildInputs = [
    pytest
    pytest-timeout
    pkgs.gcc pkgs.fpc
  ];

  # Only for tests
  buildInputs = [
    pkgs.glibc.static
  ];

  propagatedBuildInputs = [
    six
    filetracker
    simplejson
    twisted
    urllib3
    sortedcontainers
    berkeleydb
    supervisor
  ];
}
