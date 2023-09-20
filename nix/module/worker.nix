{ pkgs, lib, config, ... }:

{
  options.services.sioworker = {
    enable = lib.mkEnableOption "sioworker";

    package = lib.mkPackageOption pkgs "sioworkers" {
      default = [ "python310Packages" "sioworkers" ];
    };

    filetrackerUrl = lib.mkOption {
      default =
        if config.services.filetracker.enable or false then
          "http://${config.services.filetracker.listenAddress}:${builtins.toString config.services.filetracker.port}" else null;
      description = "The filetracker URL for the sioworker to connect to";
      type = lib.types.str;
    };

    filetrackerCache = lib.mkOption {
      default = "auto";
      description = ''
        The path of the filetracker cache for this sioworker

        IMPORTANT: The sioworker service **needs to have access to this location** and this is **not** handled automatically!!
        **You** have to ensure that the sioworker systemd service will execute with the appriopriate permissions **yourself**.
      '';
      type = with lib.types; oneOf [ (strMatching "auto") path ];
    };

    sioworkersd = lib.mkOption {
      default = { };
      description = "The sioworkersd for the sioworker to connect to";
      type = lib.types.submodule {
        options.host = lib.mkOption {
          default = "localhost";
          description = "The sioworkerd host";
          type = lib.types.str;
        };
        options.port = lib.mkOption {
          default = config.services.sioworkersd.worker.port;
          description = "The sioworkerd port";
          type = lib.types.port;
        };
      };
    };

    concurrency = lib.mkOption {
      default = "auto";
      description = "The amount of threads the sioworker should use";
      type = with lib.types; oneOf [ (strMatching "auto") ints.positive ];
    };

    memoryLimit = lib.mkOption {
      default = 1024;
      description = "The amount of memory (in megabytes) this worker will use";
      type = lib.types.ints.unsigned;
    };
  };

  config =
    let
      cfg = config.services.sioworker;
      python = cfg.package.pythonModule;
      autoFiletrackerCache = cfg.filetrackerCache == "auto";
      filetrackerCache = if autoFiletrackerCache then "/var/cache/sioworker/filetracker" else cfg.filetrackerCache;
    in
    lib.mkIf cfg.enable {
      services.filetracker-cache-cleaner.paths = lib.mkIf autoFiletrackerCache [ filetrackerCache ];

      systemd.services.sioworker = {
        enable = true;
        description = "sioworker";
        after = [ "network.target" ];
        wantedBy = [ "multi-user.target" ];

        environment = {
          PYTHONPATH = python.pkgs.makePythonPath [
            cfg.package
            # FIXME: WHY IS THIS NOT ADDED THROUGH cfg.package???
            python.pkgs.filetracker
          ];
          FILETRACKER_URL = cfg.filetrackerUrl;
          SIOWORKERS_FILETRACKER_CACHE = filetrackerCache;
          SIOWORKERS_SANDBOXES_BASEDIR = "/var/cache/sioworker/sandboxes";
        };

        script = ''
          exec ${python.pkgs.twisted}/bin/twistd --nodaemon --pidfile=/run/sioworker/sioworker.pid worker \
              --can-run-cpu-exec \
              --port ${builtins.toString cfg.sioworkersd.port} \
              -n ${lib.escapeShellArg "worker-${config.networking.hostName}"} \
              -c ${if cfg.concurrency == "auto" then  "$(nproc)" else builtins.toString cfg.concurrency} \
              -r ${builtins.toString cfg.memoryLimit} ${cfg.sioworkersd.host}
        '';

        serviceConfig = {
          Type = "simple";

          RuntimeDirectory = "sioworker";
          CacheDirectory = "sioworker";
          AmbientCapabilities = [ "CAP_PERFMON" ];
          PIDFile = "/run/sioworker/sioworker.pid";

          User = "sioworker";
          Group = "sioworker";
          DynamicUser = true;

          PrivateDevices = true;
          ProtectKernelTunables = true;
          ProtectKernelModules = true;
          ProtectKernelLogs = true;
          ProtectControlGroups = true;
        };
      };
    };
}
