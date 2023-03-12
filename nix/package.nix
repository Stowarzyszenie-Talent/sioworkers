{ pkgs
, stdenv
, lib
, buildPythonPackage

, six
, filetracker
, simplejson
, twisted
, urllib3
, sortedcontainers
, bsddb3

, pytest
, pytest-runner
, pytest-timeout

, ...
}:

buildPythonPackage {
  pname = "sioworkers";
  version = "1.0";

  src = builtins.path {
    path = ./..;
    filter = path: type: builtins.match ".*/nix" path == null;
  };

  doCheck = false;

  # HACK: This hack works around an issue where the sioworker looks for pytest things when it really doesn't have to
  patches = [ ./setup-patch.patch ];

  nativeBuildInputs = [
    pytest
    pytest-runner
    pytest-timeout
  ];

  propagatedBuildInputs = [
    six
    filetracker
    simplejson
    twisted
    urllib3
    sortedcontainers
    bsddb3
  ];
}

