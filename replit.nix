{ pkgs }: {
  deps = [
    pkgs.sqlite-interactive
    pkgs.python311
    pkgs.python311Packages.flask
  ];
}
