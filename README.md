Hari Sekhon PyTools
===================
[![Build Status](https://travis-ci.org/HariSekhon/pytools.svg?branch=master)](https://travis-ci.org/HariSekhon/pytools)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f7af72140c3b408b9659207ced17544f)](https://www.codacy.com/app/harisekhon/pytools)
[![GitHub stars](https://img.shields.io/github/stars/harisekhon/pytools.svg)](https://github.com/harisekhon/pytools/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/harisekhon/pytools.svg)](https://github.com/harisekhon/pytools/network)
[![Dependency Status](https://gemnasium.com/badges/github.com/HariSekhon/pytools.svg)](https://gemnasium.com/github.com/HariSekhon/pytools)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20OS%20X-blue.svg)](https://github.com/harisekhon/pytools#hari-sekhon-pytools)
[![DockerHub](https://img.shields.io/badge/docker-available-blue.svg)](https://hub.docker.com/r/harisekhon/pytools/)
[![](https://images.microbadger.com/badges/image/harisekhon/pytools.svg)](http://microbadger.com/#/images/harisekhon/pytools)

### Hadoop, Spark / PySpark, HBase, Pig, Ambari, IPython and Linux Tools ###

A few of the Big Data, NoSQL & Linux tools I've written over the years. All programs have `--help` to list the available options.

For many more tools see the [Tools](https://github.com/harisekhon/tools) and [Advanced Nagios Plugins Collection](https://github.com/harisekhon/nagios-plugins) repos which contains many Hadoop, NoSQL, Web and infrastructure tools and Nagios plugins.

Hari Sekhon

Big Data Contractor, United Kingdom

https://www.linkedin.com/in/harisekhon

##### Make sure you run ```make update``` if updating and not just ```git pull``` as you will often need the latest library submodule and possibly new upstream libraries. #####

### Quick Start ###

#### Ready to run Docker image #####

All programs and their pre-compiled dependencies can be found ready to run on [DockerHub](https://hub.docker.com/r/harisekhon/pytools/).

List all programs:
```
docker run harisekhon/pytools
```
Run any given program:
```
docker run harisekhon/pytools <program> <args>
```

#### Automated Build from source #####

```
git clone https://github.com/harisekhon/pytools
cd pytools
make
```

Make sure to read [Detailed Build Instructions](https://github.com/HariSekhon/pytools#detailed-build-instructions) further down for more information.

Some Hadoop tools with require Jython, see [Jython for Hadoop Utils](https://github.com/harisekhon/pytools#jython-for-hadoop-utils) for details.

### Usage ###

All programs come with a ```--help``` switch which includes a program description and the list of command line options.

Environment variables are supported for convenience and also to hide credentials from being exposed in the process list eg. ```$PASSWORD```, ```$TRAVIS_TOKEN```. These are indicated in the ```--help``` descriptions in brackets next to each option and often have more specific overrides with higher precedence eg. ```$AMBARI_HOST```, ```$HBASE_HOST``` take priority over ```$HOST```.

### PyTools ###

See ```validate_*.py``` data and config file validators further down which are useful to use in conjunction with these data converters.

- [Spark](https://spark.apache.org/):
  - ```spark_avro_to_parquet.py``` - PySpark Avro => Parquet converter
  - ```spark_parquet_to_avro.py``` - PySpark Parquet => Avro converter
  - ```spark_csv_to_avro.py``` - PySpark CSV => Avro converter, supports both inferred and explicit schemas
  - ```spark_csv_to_parquet.py``` - PySpark CSV => Parquet converter, supports both inferred and explicit schemas
  - ```spark_json_to_avro.py``` - PySpark JSON => Avro converter
  - ```spark_json_to_parquet.py``` - PySpark JSON => Parquet converter
- Data Format Converters:
  - ```json_to_xml.py``` - JSON to XML converter
  - ```xml_to_json.py``` - XML to JSON converter
  - ```json_docs_to_bulk_multiline.py``` - converts json files to bulk multi-record one-line-per-json-document format for pre-processing and loading to big data systems like [Hadoop](http://hadoop.apache.org/) and [MongoDB](https://www.mongodb.com/), can recurse directory trees, and mix json-doc-per-file / bulk-multiline-json / directories / standard input, combines all json documents and outputs bulk-one-json-document-per-line to standard output for convenient command line chaining and redirection, optionally continues on error, collects broken records to standard error for logging and later reprocessing for bulk batch jobs, even supports single quoted json while not technically valid json is used by MongoDB and even handles embedded double quotes in 'single quoted json'
- ```find_duplicate_files.py``` - finds duplicate files in one or more directory trees via multiple methods including file basename, size, MD5 comparison of same sized files, or bespoke regex capture of partial file basename
- [Ambari](https://hortonworks.com/apache/ambari/):
  - ```ambari_blueprints.py``` - Blueprint cluster templating and deployment tool using Ambari API
    - list blueprints
    - fetch all blueprints or a specific blueprint to local json files
    - blueprint an existing cluster
    - create a new cluster using a blueprint
    - sorts and prettifies the resulting JSON template for deterministic config and line-by-line diff necessary for proper revision control
    - optionally strips out the excessive and overly specific configs to create generic more reusable templates
    - see the ```ambari_blueprints/``` directory for a variety of Ambari blueprint templates generated by and deployable using this tool
  - ```ambari_ams_*.sh``` - query the Ambari Metrics Collector API for a given metrics, list all metrics or hosts
  - ```ambari_cancel_all_requests.sh``` - cancel all ongoing operations using the Ambari API
  - ```ambari_trigger_service_checks.py``` - trigger service checks using the Ambari API
- [Hadoop](http://hadoop.apache.org/) HDFS:
  - ```hadoop_hdfs_time_block_reads.jy``` - HDFS per-block read timing debugger with datanode and rack locations for a given file or directory tree. Reports the slowest Hadoop datanodes in descending order at the end. Helps find cluster data layer bottlenecks such as slow datanodes, faulty hardware or misconfigured top-of-rack switch ports.
  - ```hadoop_hdfs_files_native_checksums.jy``` - fetches native HDFS checksums for quicker file comparisons (about 100x faster than doing hdfs dfs -cat | md5sum)
  - ```hadoop_hdfs_files_stats.jy``` - fetches HDFS file stats. Useful to generate a list of all files in a directory tree showing block size, replication factor, underfilled blocks and small files
- [HBase](https://hbase.apache.org/):
  - ```hbase_generate_data.py``` - inserts random generated data in to a given [HBase](https://hbase.apache.org/) table, with optional skew support with configurable skew percentage. Useful for testing region splitting, balancing, CI tests etc. Outputs stats for number of rows written, time taken, rows per sec and volume per sec written.
  - ```hbase_show_table_region_ranges.py``` - dumps HBase table region ranges information, useful when pre-splitting tables
  - ```hbase_table_region_row_distribution.py``` - calculates the distribution of rows across regions in an HBase table, giving per region row counts and % of total rows for the table as well as median and quartile row counts per regions
  - ```hbase_table_row_key_distribution.py``` - calculates the distribution of row keys by configurable prefix length in an HBase table, giving per prefix row counts and % of total rows for the table as well as median and quartile row counts per prefix
  - ```hbase_compact_tables.py``` - compacts HBase tables (for off-peak compactions). Defaults to finding and iterating on all tables or takes an optional regex and compacts only matching tables.
  - ```hbase_flush_tables.py``` - flushes HBase tables. Defaults to finding and iterating on all tables or takes an optional regex and flushes only matching tables.
  - ```hbase_regions_by_*size.py``` - queries given RegionServers JMX to lists topN regions by storeFileSize or memStoreSize, ascending or descending
  - ```hbase_region_requests.py``` - calculates requests per second per region across all given RegionServers or average since RegionServer startup, configurable intervals and count, can filter to any combination of reads / writes / total requests per second. Useful for watching more granular region stats to detect region hotspotting
  - ```hbase_regionserver_requests.py``` - calculates requests per regionserver second across all given regionservers or average since regionserver(s) startup(s), configurable interval and count, can filter to any combination of read, write, total, rpcScan, rpcMutate, rpcMulti, rpcGet, blocked per second. Useful for watching more granular RegionServer stats to detect RegionServer hotspotting
  - ```hbase_regions_least_used.py``` - finds topN biggest/smallest regions across given RegionServers than have received the least requests (requests below a given threshold)
- [OpenTSDB](http://opentsdb.net/):
  - ```opentsdb_import_metric_distribution.py``` - calculates metric distribution in bulk import file(s) to find data skew and help avoid HBase region hotspotting
  - ```opentsdb_list_metrics.sh``` - lists OpenTSDB metric names, tagk or tagv from HBase and optionally their created date, sorted ascending
- [Pig](https://pig.apache.org/)
  - ```pig-text-to-elasticsearch.pig``` - bulk index unstructured files in [Hadoop](http://hadoop.apache.org/) to [Elasticsearch](https://www.elastic.co/products/elasticsearch)
  - ```pig-text-to-solr.pig``` - bulk index unstructured files in [Hadoop](http://hadoop.apache.org/) to [Solr](http://lucene.apache.org/solr/) / [SolrCloud clusters](https://wiki.apache.org/solr/SolrCloud)
  - ```pig_udfs.jy``` - Pig Jython UDFs for Hadoop
- ```ipython-notebook-pyspark.py``` - per-user authenticated IPython Notebook + PySpark integration to allow each user to auto-create their own password protected IPython Notebook running Spark
- [Docker](https://www.docker.com/):
  - ```docker_registry_show_tags.py``` / ```dockerhub_show_tags.py``` / ```quay_show_tags.py``` - shows tags for docker repos in a docker registry or on [DockerHub](https://hub.docker.com/u/harisekhon/) or [Quay.io](https://quay.io/) - Docker CLI doesn't support this yet but it's a very useful thing to be able to see live on the command line or use in shell scripts (use `-q`/`--quiet` to return only the tags for easy shell scripting). You can use this to pre-download all tags of a docker image before running tests across versions in a simple bash for loop, eg. ```docker_pull_all_tags.sh```
  - ```dockerhub_search.py``` - search DockerHub with a configurable number of returned results (official `docker search` is limited to only 25 results), using `--verbose` will also show you how many results were returned to the termainal and how many DockerHub has in total (use ```-q / --quiet``` to return only the image names for easy shell scripting). This can be used to download all of my DockerHub images in a simple bash for loop eg. ```docker_pull_all_images.sh``` and can be chained with ```dockerhub_show_tags.py``` to download all tagged versions for all docker images eg. ```docker_pull_all_images_all_tags.sh```
  - ```dockerfiles_check_git*.py``` - check Git tags & branches align with the containing Dockerfile's ```ARG *_VERSION```
- ```find_active_server.py``` - generic solution to return the first available healthy server or active master in high availability deployments, useful for chaining with single argument tools. Configurable tests include socket, http, https, ping, url and/or regex content match, multi-threaded for speed. Designed to extend tools that only accept a single ```--host``` option but for which the technology has later added multi-master support or active-standby masters (eg. Hadoop, HBase) or where you want to query cluster wide information available from any online peer (eg. Elasticsearch)
  - The following are simplified specialisations of the above program, just pass host arguments, all the details have been baked in, no switches required
    - ```find_active_hadoop_namenode.py``` - finds the active [Hadoop](http://hadoop.apache.org/) Namenode in HDFS HA
    - ```find_active_hadoop_resource_manager.py``` - finds the active [Hadoop](http://hadoop.apache.org/) Resource Manager in Yarn HA
    - ```find_active_hbase_master.py``` - finds the active [HBase](https://hbase.apache.org/) Master in HBase HA
    - ```find_active_hbase_thrift.py``` - finds the first available [HBase](https://hbase.apache.org/) Thrift Server (run multiple of these for load balancing)
    - ```find_active_hbase_stargate.py``` - finds the first available [HBase](https://hbase.apache.org/) Stargate rest server (run multiple of these for load balancing)
    - ```find_active_apache_drill.py``` - finds the first available [Apache Drill](https://drill.apache.org/) node
    - ```find_active_impala*.py``` - finds the first available [Impala](https://impala.apache.org/) node of either Impalad, Catalog or Statestore
    - ```find_active_presto_coordinator.py``` - finds the first available [Presto](https://prestodb.io/) Coordinator
    - ```find_active_oozie.py``` - finds the first active [Oozie](http://oozie.apache.org/) server
    - ```find_active_solrcloud.py``` - finds the first available [Solr](http://lucene.apache.org/solr/) / [SolrCloud](https://wiki.apache.org/solr/SolrCloud) node
    - ```find_active_elasticsearch.py``` - finds the first available [Elasticsearch](https://www.elastic.co/products/elasticsearch) node
    - see also: [Advanced HAProxy configurations](https://github.com/harisekhon/nagios-plugins/tree/master/haproxy) which are part of the [Advanced Nagios Plugins Collection](https://github.com/harisekhon/nagios-plugins)
- ```travis_debug_session.py``` - launches a [Travis CI](https://travis-ci.org/) interactive debug build session via Travis API, tracks session creation and drops user straight in to the SSH shell on the remote Travis build, very convenient one shot debug launcher for Travis CI
- ```validate_*.py``` - validate files, directory trees and/or standard input streams
  - supports the following file formats:
    - Avro
    - CSV
    - INI / Java Properties (also detects duplicate sections and duplicate keys within sections)
    - JSON (both normal and json-doc-per-line bulk / big data format as found in MongoDB and Hadoop json data files)
    - LDAP LDIF
    - Parquet
    - XML
    - YAML
  - directories are recursed, testing any files with relevant matching extensions (`.avro`, `.csv`, `json`, `parquet`, `.ini`/`.properties`, `.ldif`, `.xml`, `.yml`/`.yaml`)
  - used for Continuous Integration tests of various adjacent Spark data converters as well as configuration files for things like Presto, Ambari, Apache Drill etc found in my [DockerHub](https://hub.docker.com/u/harisekhon/) images [Dockerfiles master repo](https://github.com/HariSekhon/Dockerfiles) which contains docker builds and configurations for many open source Big Data & Linux technologies
- ```welcome.py``` - cool spinning welcome message greeting your username and showing last login time and user to put in your shell's ```.profile``` (there is also a perl version in my [Tools](https://github.com/harisekhon/tools) repo)

### Detailed Build Instructions

#### Manual Setup

Enter the pytools directory and run git submodule init and git submodule update to fetch my library repo:

```
git clone https://github.com/harisekhon/pytools
cd pytools
git submodule init
git submodule update
pip install -r requirements.txt
```


#### Offline Setup

Download the PyTools and Pylib git repos as zip files:

https://github.com/HariSekhon/pytools/archive/master.zip

https://github.com/HariSekhon/pylib/archive/master.zip

Unzip both and move Pylib to the ```pylib``` folder under PyTools.

```
unzip pytools-master.zip
unzip pylib-master.zip

mv pytools-master pytools
mv pylib-master pylib
mv -f pylib pytools/
```

Proceed to install PyPI modules for whichever programs you want to use using your usual procedure - usually an internal mirror or proxy server to PyPI, or rpms / debs (some libraries are packaged by Linux distributions).

All PyPI modules are listed in the ```requirements.txt``` file.


##### Mac OS X

The automated build also works on Mac OS X but you'll need to download and install [Apple XCode](https://developer.apple.com/download/). I also recommend you get [HomeBrew](https://brew.sh/) to install other useful tools and libraries you may need like OpenSSL for development headers and tools such as wget (these are installed automatically if Homebrew is detected on Mac OS X):

```
brew install openssl wget
```

CPAN's Crypt::SSLeay may not find the OpenSSL header and error like so:

```
fatal error: 'openssl/opensslv.h' file not found
#include <openssl/opensslv.h>
```

In this case, give it the path to the OpenSSL lib to build:

```
sudo OPENSSL_INCLUDE=/usr/local/opt/openssl/include OPENSSL_LIB=/usr/local/opt/openssl/lib cpan Crypt::SSLeay
```

then continue with the rest of the build:

```
make
```

You may get errors trying to install to Python library paths even as root on newer versions of Mac, sometimes this is caused by pip 10 vs pip 9 and downgrading will work around it:

```
pip install --upgrade pip==9.0.1
make
pip install --upgrade pip
make
```

### Jython for Hadoop Utils ###

The 3 Hadoop utility programs listed below require Jython (as well as Hadoop to be installed and correctly configured)

```
hadoop_hdfs_time_block_reads.jy
hadoop_hdfs_files_native_checksums.jy
hadoop_hdfs_files_stats.jy
```

Run like so:
```
jython -J-cp `hadoop classpath` hadoop_hdfs_time_block_reads.jy --help
```

The ```-J-cp `hadoop classpath` ``` bit does the right thing in finding the Hadoop java classes required to use the Hadoop APIs.

See below for procedure to install Jython if you don't already have it.

##### Automated Jython Install

```
make jython-install
```

##### Manual Jython Install

Jython is a simple download and unpack and can be fetched from http://www.jython.org/downloads.html

Then add the Jython untarred directory to the $PATH or specify the /path/to/jythondir/bin/jython explicitly when calling jython.

#### Configuration for Strict Domain / FQDN validation ####

Strict validations include host/domain/FQDNs using TLDs which are populated from the official IANA list is done via my [PyLib](https://github.com/harisekhon/pylib) library submodule - see there for details on configuring this to permit custom TLDs like ```.local``` or ```.intranet``` (both supported by default).

#### Python SSL certificate verification problems

If you end up with an error like:
```
./dockerhub_show_tags.py centos ubuntu
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:765)
```
It can be caused by an issue with the underlying Python + libraries due to changes in OpenSSL and certificates. One quick fix is to do the following:
```
pip uninstall -y certifi && pip install certifi==2015.04.28
```

### Updating ###

Run ```make update```. This will git pull and then git submodule update which is necessary to pick up corresponding library updates.

If you update often and want to just quickly git pull + submodule update but skip rebuilding all those dependencies each time then run ```make update-no-recompile``` (will miss new library dependencies - do full ```make update``` if you encounter issues).

### Testing

[Continuous Integration](https://travis-ci.org/HariSekhon/pytools) is run on this repo with tests for success and failure scenarios:
- unit tests for the custom supporting [python library](https://github.com/harisekhon/pylib)
- integration tests of the top level programs using the libraries for things like option parsing
- [functional tests](https://github.com/HariSekhon/pytools/tree/master/tests) for the top level programs using local test data and [Docker containers](https://hub.docker.com/u/harisekhon/)

To trigger all tests run:

```
make test
```

which will start with the underlying libraries, then move on to top level integration tests and functional tests using docker containers if docker is available.

### Contributions ###

Patches, improvements and even general feedback are welcome in the form of GitHub pull requests and issue tickets.

### See Also ###

* [Tools](https://github.com/harisekhon/tools) - 30+ tools for Hadoop, NoSQL, Solr, Elasticsearch, Pig, Hive, Web URL + Nginx stats watchers, SQL and NoSQL syntax recasers, various Linux CLI tools

* [The Advanced Nagios Plugins Collection](https://github.com/harisekhon/nagios-plugins) - 400+ programs for Nagios monitoring your Hadoop & NoSQL clusters. Covers every Hadoop vendor's management API and every major NoSQL technology (HBase, Cassandra, MongoDB, Elasticsearch, Solr, Riak, Redis etc.) as well as message queues (Kafka, RabbitMQ), continuous integration (Jenkins, Travis CI) and traditional infrastructure (SSL, Whois, DNS, Linux)

* [PyLib](https://github.com/harisekhon/pylib) - my personal python library leveraged in this repo as a submodule

* [Perl Lib](https://github.com/harisekhon/lib) - Perl version of above library

* [Spark Apps eg. Spark => Elasticsearch](https://github.com/harisekhon/spark-to-elasticsearch) - Scala application to index from Spark to Elasticsearch. Used to index data in Hadoop clusters or local data via Spark standalone. This started as a Scala Spark port of ```pig-text-to-elasticsearch.pig``` from this repo.

You might also be interested in the following really nice Jupyter notebook for HDFS space analysis created by another Hortonworks guy Jonas Straub:

* https://github.com/mr-jstraub/HDFSQuota/blob/master/HDFSQuota.ipynb
