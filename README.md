# norns-catalog

The [norns](https://monome.org/docs/norns/) catalog mechanism consists of two
parts. The first part is the "catalog" itself which is a single JSON file
listing scripts available for installation. The second part is a "source"
configuration file which tells a norns device where to download a given catalog
file.

The [maiden](https://monome.org/docs/norns/maiden/) web ui displays the set of
catalogs (sources) configured on a given device. Two catalogs, `base` and
`community`, are configured by default as part of `norns` software installation.
The catalog source files can be found in the `data/sources` folder within the
file explorer.

_This repository is intended to show how one can create their own personal
catalog or a catalog for a focused community._

## Adding Static Catalogs

New catalogs can be added to a device defining an additional source. In `maiden`
select the `data/sources` folder and create a file called `<name>.json`. Within
that file tell the device where to find the file to download.

Example for the "base" catalog:

```json
{
  "file_info": {
    "version": 1,
    "kind": "catalog_source"
  },
  "source": {
      "name": "base",
      "method": "download",
      "parameters": {
          "url": "https://raw.githubusercontent.com/monome/norns-community/main/base.json"
      }
  }
}
```

* set the `name` property to control what the `maiden`  ui will display
* set the `url` property to point to any `http`/`https` location the device can reach

## Dynamic Catalogs

This repostory provides an example of one way to build or serve a catalog file
dynamically. A Python script assembles individual JSON files, one per entry,
into a file catalog. There is nothing special about this example - any tool or
process can be used as long as it produces "source" files which follow the
[source schema](https://raw.githubusercontent.com/monome/maiden/refs/heads/main/pkg/catalog/source.schema.json) and "catalog" files which follow the [catalog schema](https://raw.githubusercontent.com/monome/maiden/refs/heads/main/pkg/catalog/catalog.schema.json).

### Setup

The script uses a configuration file to specify (among other things) then name
of the catalog itself. In order to use the script the `config.json` file must
exist at the root of the repository, this most easily accomplished by using the
`setup` sub-command:

```sh
./catalog.sh setup --name demo
```

*NOTE:* If using Windows the `./catalog.ps1` script can be used.

### Building

The `build` sub-command assembles the entries, sorts them alphabetically by
name, and validates the schema - if all is correct it prints the result JSON
data to stdout or to a file if a file name is provided on the command line.

```sh
# build and write to catalog.json
./catalog.sh build catalog.json

# dump the contents of catalog.json
cat catalog.json
{
  "file_info": {
    "version": 1,
    "kind": "script_catalog"
  },
  "catalog_name": "demo",
  "date": "2026-11-02T02:37:56Z",
  "entries": [
    {
      "project_name": "ash",
      "project_url": "https://github.com/tehn/ash",
      "author": "tehn",
      "description": "a small collection",
      "discussion_url": "https://llllllll.co/t/ash-a-small-collection/21349",
      "tags": [
        "arc",
        "grid",
        "looper",
        "drum",
        "synth"
      ]
    },
    {
      "project_name": "awake",
      "project_url": "https://github.com/tehn/awake",
      "author": "tehn",
      "description": "time changes",
      "discussion_url": "https://llllllll.co/t/awake/21022",
      "tags": [
        "sequencer",
        "grid"
      ]
    }
  ]
}
```

The resulting catalog file could be stored in git, uploaded to a website, or
manually copied to the "dust/data/catalogs" folder on a given device.

The `build` sub-command includes options to include/exclude entries based on
tags if desired. This sub-command could be useful as part of a catalog CI or
publishing pipeline.

```sh
./catalog.sh build --help
usage: catalog build [-h] [--config CONFIG] [--entries ENTRIES] [--template TEMPLATE] [--include TAG] [--exclude TAG] [output]

positional arguments:
  output               Optional output file path; writes to stdout when omitted

options:
  -h, --help           show this help message and exit
  --config CONFIG      Path to config.json (defaults to the repository root config.json)
  --entries ENTRIES    Directory containing entry JSON files (defaults to <config-dir>/entries)
  --template TEMPLATE  Path to the Jinja2 catalog template (defaults to tools/templates/catalog.json.j2)
  --include TAG        Only include entries that have any of these tags (repeatable; default: all entries)
  --exclude TAG        Exclude entries that have any of these tags (repeatable; applied after --include)
```

### Serving via HTTP

The `serve` sub-command provides an example HTTP server which responsed to
requests for the catalog, building it if need be. The `entries` directory is
watched so that files added or removed from that directory are immediately
reflected in the resulting catalog.

`serve` builds the full catalog into memory, serves it over HTTP at `/`,
`/catalog.json`, and `/<catalog_name>.json`, and rebuilds whenever files in
`entries/` change.

From the root of the repostory:

```sh
./catalog.sh serve
catalog ready (2 entries)
serving catalog on http://127.0.0.1:8000/
watching /Users/greg/proj/norns-catalog/entries
```

In a different shell:

```sh
# the catalog is served from a number of URLs, site root
curl http://127.0.0.1:8000/
# generic "catalog.json"
curl http://127.0.0.1:8000/catalog.json
# explicitly named
curl http://127.0.0.1:8000/demo.json
```

This basic server could be extended to support query args as part of the URL in
order to provide server side filtering based on tags (for example).

### Entry format

Each file in `entries/` is a single maiden catalog entry object, for example:

```json
{
  "project_name": "awake",
  "project_url": "https://github.com/tehn/awake",
  "author": "tehn",
  "description": "time changes",
  "discussion_url": "https://llllllll.co/t/awake/21022",
  "tags": ["sequencer", "grid"]
}
```

`project_name` and `project_url` are required. See the [catalog
schema](https://raw.githubusercontent.com/monome/maiden/refs/heads/main/pkg/catalog/catalog.schema.json)
for the full field set.

## Requirements

* [uv](https://docs.astral.sh/uv/)
* Python 3.12+ (installed automatically by uv if needed)
* `git` with a GitHub `origin` remote (used by `build-source`)

## Quick start

```bash
cd tools && uv sync && cd ..
./catalog.sh setup --name community
./catalog.sh build community.json
./catalog.sh build-source community-source.json
./catalog.sh serve
```

```powershell
cd tools; uv sync; cd ..
.\catalog.ps1 setup --name community
.\catalog.ps1 build community.json
.\catalog.ps1 build-source community-source.json
.\catalog.ps1 serve
```

`setup` writes `config.json`. Other commands require that file.

## License

See [LICENSE](LICENSE).
