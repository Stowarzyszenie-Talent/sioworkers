{
  description = "Filetracker caching file storage";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/release-22.11";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.filetracker.url = "github:Stowarzyszenie-Talent/filetracker";

  outputs = { self, nixpkgs, flake-utils, filetracker }: {
    overlays.default = final: prev: {
      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (python-final: python-prev: {
          sioworkers = prev.callPackage ./nix/package.nix python-prev;
        })
      ];

      sioworkers = with final.python38Packages; toPythonApplication sioworkers;
    };

    nixosModules.default = {
      imports = [
        filetracker.nixosModules.default
        ./nix/module
      ];
    };
    nixosConfigurations.container = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";

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
