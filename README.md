Hari Sekhon PyTools
===================
[![Build Status](https://travis-ci.org/HariSekhon/pytools.svg?branch=master)](https://travis-ci.org/HariSekhon/pytools)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f7af72140c3b408b9659207ced17544f)](https://www.codacy.com/app/harisekhon/pytools)
[![Dependency Status](https://gemnasium.com/badges/github.com/HariSekhon/pytools.svg)](https://gemnasium.com/github.com/HariSekhon/pytools)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20OS%20X-blue.svg)](https://github.com/harisekhon/pytools#hari-sekhon-pytools)
[![DockerHub](https://img.shields.io/badge/docker-available-blue.svg)](https://hub.docker.com/r/harisekhon/pytools/)
[![](https://images.microbadger.com/badges/image/harisekhon/pytools.svg)](http://microbadger.com/#/images/harisekhon/pytools)

### Hadoop, Spark / PySpark, HBase, Pig, Ambari, IPython and Linux Tools ###

A few of the Hadoop, Spark & Linux tools I've written over the years. All programs have --help to list the available options.

For many more tools see the [Tools](//github.com/harisekhon/tools) and [Advanced Nagios Plugins Collection](//github.com/harisekhon/nagios-plugins) repos which contains many Hadoop, NoSQL, Web and infrastructure tools and Nagios plugins.

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
Some Hadoop tools with require Jython, see [Jython for Hadoop Utils](https://github.com/harisekhon/pytools#jython-for-hadoop-utils) for details.

### Usage ###

All programs come with a ```--help``` switch which includes a program description and the list of command line options.

Some common options also support optional environment variables for convenience to reduce repeated --switch usage or to hide them from being exposed in the process list. These are indicated in the --help descriptions in brackets next to each option eg. $HOST or more specific ones with higher precedence like $AMBARI_HOST.

### PyTools ###

- ```ambari_blueprints.py``` - Ambari Blueprint tool using Ambari API to find and fetch all blueprints or a specific blueprint to local json files, blueprint an existing cluster, or create a new cluster using a blueprint. Sorts and prettifies the resulting JSON template, and optionally strips out the excessive and overly specific configs to create generic more reusable templates. See adjacent ```ambari_blueprints``` directory for a variety of Ambari blueprint templates generated using this tool
- ```hadoop_hdfs_time_block_reads.jy``` - Hadoop HDFS per-block read timing debugger with datanode and rack locations for a given file or directory tree. Reports the slowest Hadoop datanodes in descending order at the end. Helps find cluster data layer bottlenecks such as slow datanodes, faulty hardware or misconfigured top-of-rack switch ports.
- ```hadoop_hdfs_files_native_checksums.jy``` - fetches native HDFS checksums for quicker file comparisons (about 100x faster than doing hdfs dfs -cat | md5sum)
- ```hadoop_hdfs_files_stats.jy``` - fetches HDFS file stats. Useful to generate a list of all files in a directory tree showing block size, replication factor, underfilled blocks and small files
- ```hbase_compact_tables.py``` - compacts HBase tables (for off-peak compactions). Defaults to finding and iterating on all tables or takes an optional regex and compacts only matching tables.
- ```pig-text-to-elasticsearch.pig``` / ```pig-text-to-solr.pig``` - bulk indexes unstructured files in Hadoop to Elasticsearch or Solr/SolrCloud clusters
- ```pig_udfs.jy``` - Pig Jython UDFs for Hadoop
- ```ipython-notebook-pyspark.py``` - per-user authenticated IPython Notebook + PySpark integration to allow each user to auto-create their own password protected IPython Notebook running Spark
- ```spark_avro_to_parquet.py``` - PySpark Avro => Parquet converter
- ```spark_parquet_to_avro.py``` - PySpark Parquet => Avro converter
- ```spark_csv_to_avro.py``` - PySpark CSV => Avro converter, supports both inferred and explicit schemas
- ```spark_csv_to_parquet.py``` - PySpark CSV => Parquet converter, supports both inferred and explicit schemas
- ```spark_json_to_avro.py``` - PySpark JSON => Avro converter
- ```spark_json_to_parquet.py``` - PySpark JSON => Parquet converter
- ```dockerhub_show_tags.py``` - shows DockerHub tags - Docker CLI doesn't support this yet but it's a very useful thing to be able to see live on the command line or use in shell scripts (use ```-q``` to return only the tags for piping to other commands)
- ```dockerhub_search.py``` - search DockerHub with a configurable number of returned results (official ```docker search``` is limited to only 25 results)
- ```dockerfiles_check_git*.py``` - check Git tags & branches align with the containing Dockerfile's ```ARG *_VERSION```
- ```welcome.py``` - cool spinning welcome message greeting your username and showing last login time and user (there is also a perl version in my [Tools](https://github.com/harisekhon/tools) repo)
- ```find_duplicate_files.py``` - finds duplicate files in one or more directory trees via multiple methods including file basename, size, MD5 comparison of same sized files, or bespoke regex capture of partial file basename 
- ```travis_debug_session.py``` - triggers a Travis CI debug build session via Travis API, tracks the session starting and being ready and then drops user straight in to the shell on the Travis build, very convenient one shot remote debug launcher.
- ```validate_*.py``` - validate files, directory trees and/or standard input streams for the following file types: Avro, CSV, JSON, Parquet, XML, YAML. Directories are recursed, testing any files with relevant matching extensions (```.avro```, ```.csv```, ```.json```, ```.parquet```, ```.xml```, ```.yml```/```.yaml```). ```validate_json.py``` supports both normal json files as well as json-doc-per-line files such as MongoDB or Hadoop json data files


#### Manual Setup ####

Enter the pytools directory and run git submodule init and git submodule update to fetch my library repo:

```
git clone https://github.com/harisekhon/pytools
cd pytools
git submodule init
git submodule update
pip install -r requirements.txt
```

### Jython for Hadoop Utils ###

The 3 Hadoop utility programs listed below require Jython (as well as Hadoop to be installed and correctly configured or course)

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

### Contributions ###

Patches, improvements and even general feedback are welcome in the form of GitHub pull requests and issue tickets.

### See Also ###

* [Tools](https://github.com/harisekhon/tools) - 30+ tools for Hadoop, NoSQL, Solr, Elasticsearch, Pig, Hive, Web URL + Nginx stats watchers, SQL and NoSQL syntax recasers, various Linux CLI tools

* [The Advanced Nagios Plugins Collection](https://github.com/harisekhon/nagios-plugins) - 220+ programs for Nagios monitoring your Hadoop & NoSQL clusters. Covers every Hadoop vendor's management API and every major NoSQL technology (HBase, Cassandra, MongoDB, Elasticsearch, Solr, Riak, Redis etc.) as well as traditional Linux and infrastructure.

* [PyLib](https://github.com/harisekhon/pylib) - my personal python library leveraged in this repo as a submodule

* [Perl Lib](https://github.com/harisekhon/lib) - Perl version of above library

* [Spark Apps eg. Spark => Elasticsearch](https://github.com/harisekhon/spark-to-elasticsearch) - Scala application to index from Spark to Elasticsearch. Used to index data in Hadoop clusters or local data via Spark standalone. This started as a Scala Spark port of ```pig-text-to-elasticsearch.pig``` from this repo.
