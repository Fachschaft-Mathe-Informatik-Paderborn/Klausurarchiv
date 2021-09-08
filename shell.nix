{ pkgs ? import <nixpkgs> {} }:
let 
    pythonEnv = pkgs.python3.withPackages(ps: with ps; [ fuzzywuzzy flask pytest ]);
in
pkgs.mkShell rec {
  packages = with pkgs; [ pythonEnv doxygen ];
}
