{ pkgs, lib, config, ... }:

{
  options.services.sioworkersd = {
    enable = lib.mkEnableOption "sioworkersd";

    package = lib.mkPackageOption pkgs "sioworkers" {
      default = [ "python38Packages" "sioworkers" ];
    };

    taskMemoryLimit = lib.mkOption {
      default = 2048;
      description = "Maximum task required RAM (in MiB) allowed by the scheduler";
      type = lib.types.ints.unsigned;
    };


    worker = lib.mkOption {
      default = { };
      description = "The worker listen address and port";
      type = lib.types.submodule {
        options.listen = lib.mkOption {
          default = "";
          description = "The worker listen address";
          type = lib.types.str;
        };
        options.port = lib.mkOption {
          default = 7888;
          description = "The worker listen port";
          type = lib.types.port;
        };
      };
    };

    rpc = lib.mkOption {
      default = { };
      description = "The RPC listen address and port";
      type = lib.types.submodule {
        options.listen = lib.mkOption {
          default = "";
          description = "The RPC listen address";
          type = lib.types.str;
        };
        options.port = lib.mkOption {
          default = 7889;
          description = "The RPC listen port";
          type = lib.types.port;
        };
      };
    };
  };

  config =
    let
      cfg = config.services.sioworkersd;
      python = cfg.package.pythonModule;
    in
    lib.mkIf cfg.enable {
      systemd.services.sioworkersd = {
        enable = true;
        description = "sioworkersd";
        after = [ "network.target" ];
        wantedBy = [ "multi-user.target" ];

        before = [ "sioworker.service" ];
        requiredBy = [ "sioworker.service" ];

        environment = {
          PYTHONPATH = python.pkgs.makePythonPath [
            cfg.package
            # FIXME: WHY IS THIS NOT ADDED THROUGH cfg.package???
            python.pkgs.filetracker
          ];
        };

        script = ''
          ${python.pkgs.twisted}/bin/twistd --nodaemon -l- \
              --pidfile=/run/sioworkersd/sioworkersd.pid \
              sioworkersd \
              --database=/var/lib/sioworkersd/database.db \
              --max-task-ram ${builtins.toString cfg.taskMemoryLimit} \
              --worker-listen ${lib.escapeShellArg cfg.worker.listen} \
              --worker-port ${builtins.toString cfg.worker.port} \
              --rpc-listen ${lib.escapeShellArg cfg.rpc.listen} \
              --rpc-port ${builtins.toString cfg.rpc.port}
        '';

        serviceConfig = {
          Type = "simple";

          RuntimeDirectory = "sioworkersd";
          StateDirectory = "sioworkersd";
          PIDFile = "/run/sioworkersd/sioworkersd.pid";

          User = "sioworkersd";
          Group = "sioworkersd";
          DynamicUser = true;
        };
      };
    };
}
