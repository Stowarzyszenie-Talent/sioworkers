{ pkgs, config, ... }:

{
  boot.isContainer = true;
  networking.useDHCP = false;
  networking.hostName = "sioworker";

  services.filetracker = {
    enable = true;

    ensureFiles = {
      "/sandboxes/compiler-gcc.10_2_1.tar.gz" = pkgs.fetchurl {
        url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/compiler-gcc.10_2_1.tar.gz";
        hash = "sha256-+QO7/ZqLWRvFCF9KdVqrZ6ZsBB96bkRgYVUUezvAf8A=";
      };
      "/sandboxes/proot-sandbox_amd64.tar.gz" = pkgs.fetchurl {
        url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/proot-sandbox_amd64.tar.gz";
        hash = "sha256-u6CSak326pAa7amYqYuHIqFu1VppItOXjFyFZgpf39w=";
      };
    };
  };

  services.sioworker = {
    enable = true;

    sioworkersd = {
      host = "localhost";
      port = 7888;
    };
  };

  environment.systemPackages = with pkgs; [
    htop
    # For the `filetracker` CLI
    pkgs.filetracker
  ];

  imports = [
    ./module.nix
  ];
}
