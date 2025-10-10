{
  description = "The task runner used by SIO2";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/release-25.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.filetracker = {
    url = "github:Stowarzyszenie-Talent/filetracker";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, filetracker }:
    let
      importWithPin = file:
        ({ pkgs, lib, config, ... }: import file {
          # Use pinned nixpkgs from our input for epic reproducibility.
          pkgs = import nixpkgs {
            inherit (pkgs) system; overlays = [ self.overlays.default filetracker.overlays.default ];
          };
          inherit lib config;
        });
      selfImports = [
        (importWithPin ./nix/module/worker.nix)
        (importWithPin ./nix/module/workersd.nix)
      ];
    in
    {
      overlays.default = final: prev: {
        pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
          (python-final: python-prev: {
            sioworkers = prev.callPackage ./nix/package.nix python-prev;
          })
        ];

        sioworkers = with final.python312Packages; toPythonApplication sioworkers;
      };

      nixosModules.self = {
        nixpkgs.overlays = [ self.overlays.default ];
        imports = selfImports;
      };

      nixosModules.default = {
        nixpkgs.overlays = [ self.overlays.default ];
        imports = [ filetracker.nixosModules.default ] ++ selfImports;
      };

      nixosConfigurations.container = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        nixosModules.self = {
          nixpkgs.overlays = [ self.overlays.default ];
          imports = selfImports;
        };
        modules = [
          (_: {
            nixpkgs.overlays = [
              self.overlays.default
              filetracker.overlays.default
            ];
          })
          ./nix/container.nix
        ];
      };
    } // (flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = import nixpkgs { inherit system; overlays = [ self.overlays.default filetracker.overlays.default ]; };
      in
      {
        packages.default = pkgs.sioworkers;
        devShell = pkgs.sioworkers;
      }));
}
