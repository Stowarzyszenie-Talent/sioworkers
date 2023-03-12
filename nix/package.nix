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

