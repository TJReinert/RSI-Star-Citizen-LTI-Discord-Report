#!/usr/bin/env python3
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import semver
from git import Repo

def get_parser():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('--version', '-v', required=True, type=str,
                        help="Version of release")
    parser.add_argument('--description', '-d', required=False, type=str,
                        help="Description for release")

    return parser

def tag(raw_version, raw_description):
    version = format_version(raw_version)
    desc = format_description(raw_description, version)
    repo = Repo()
    assert not repo.bare
    repo.git.tag(a=version, m=desc)

def format_version(raw_version: str):
    if (raw_version == None):
        raise Exception("Version is required")
    
    if (semver.VersionInfo.isvalid(raw_version)):
        return f"v{raw_version}"
    
    raise Exception("Version provided is not a valid semantic version.")


def format_description(raw_description, version):
    if (raw_description == None):
        return f"{version}"
    return f"{version} - {raw_description}"

if __name__ == "__main__":
    args = get_parser().parse_args()
    tag(
        raw_version=args.version,
        raw_description=args.description
    )