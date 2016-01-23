Hari Sekhon PyTools [![Build Status](https://travis-ci.org/HariSekhon/pytools.svg?branch=master)](https://travis-ci.org/HariSekhon/pytools)
================================

### Hadoop, Spark / PySpark, Ambari, IPython, Pig and Linux Tools ###

A few of the Hadoop and other nifty "Unixy" / Linux tools I've written over the years that are generally useful across environments. All programs have --help to list the available options.

For many more tools see [Tools](//github.com/harisekhon/tools) and the [Advanced Nagios Plugins Collection](//github.com/harisekhon/nagios-plugins) which contains many Hadoop, NoSQL, Web and infrastructure tools and Nagios plugins.

Hari Sekhon

Big Data Contractor, United Kingdom

http://www.linkedin.com/in/harisekhon

##### Make sure you run ```make update``` if updating and not just ```git pull``` as you will often need the latest library submodule and possibly new upstream libraries. #####

### Quick Setup ###

The 'make' command will initialize my library submodule:

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

- ```ambari_blueprints.py``` - Ambari Blueprint tool using Ambari API to find and fetch all blueprints or a specific blueprint to local json files, blueprint an existing cluster, or create a new cluster using a blueprint. See adjacent ```ambari_blueprints``` directory for some blueprint templates
- ```hadoop_hdfs_time_block_reads.jy``` - Hadoop HDFS per-block read timing debugger with datanode and rack locations for a given file or directory tree. Reports the slowest Hadoop datanodes in descending order at the end
- ```hadoop_hdfs_files_native_checksums.jy``` - fetches native HDFS checksums for quicker file comparisons (about 100x faster than doing hdfs dfs -cat | md5sum)
- ```hadoop_hdfs_files_stats.jy``` - fetches HDFS file stats
- ```pig-text-to-elasticsearch.pig``` / ```pig-text-to-solr.pig``` - bulk indexes unstructured files in Hadoop to Elasticsearch or Solr/SolrCloud clusters
- ```pig_udfs.jy``` - Pig Jython UDFs for Hadoop
- ```ipython-notebook-pyspark.py``` - per-user authenticated IPython Notebook + PySpark integration to allow each user to auto-create their own password protected IPython Notebook running Spark
- ```spark_avro_to_parquet.py``` - PySpark Avro => Parquet converter
- ```spark_csv_to_avro.py``` - PySpark CSV => Avro converter, supports both inferred and explicit schemas
- ```spark_csv_to_parquet.py``` - PySpark CSV => Parquet converter, supports both inferred and explicit schemas
- ```spark_json_to_avro.py``` - PySpark JSON => Avro converter
- ```spark_json_to_parquet.py``` - PySpark JSON => Parquet converter
- ```validate_*.py``` - validate files, directory trees and/or standard input streams for the following file types: Avro, CSV, JSON, Parquet, XML, YAML. Directories are recursed, testing any files with relevant matching extensions (```.avro```, ```.csv```, ```.json```, ```.parquet```, ```.xml```, ```.yml```/```.yaml```). ```validate_json.py``` supports both normal json files as well as json-doc-per-line files such as MongoDB or Hadoop json data files
- ```welcome.py``` - cool spinning welcome message greeting your username and showing last login time and user (there also a perl version in my [Tools](https://github.com/harisekhon/tools) repo)

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

Jython is a simple download and unpack and can be fetched from http://www.jython.org/downloads.html

Then add the Jython untarred directory to the $PATH or specify the /path/to/jythondir/bin/jython explicitly:

```
/path/to/jython-x.y.z/bin/jython -J-cp `hadoop classpath` hadoop_hdfs_time_block_reads.jy --help
```

The ```-J-cp `hadoop classpath` ``` bit does the right thing in finding the Hadoop java classes required to use the Hadoop APIs.

#### Configuration for Strict Domain / FQDN validation ####

Strict validations include host/domain/FQDNs using TLDs which are populated from the official IANA list is done via my [PyLib](https://github.com/harisekhon/pylib) library submodule - see there for details on configuring this to permit custom TLDs like ```.local``` or ```.intranet``` (both supported by default).

### Updating ###

Run ```make update```. This will git pull and then git submodule update which is necessary to pick up corresponding library updates.

If you update often and want to just quickly git pull + submodule update but skip rebuilding all those dependencies each time then run ```make update-no-recompile``` (will miss new library dependencies - do full ```make update``` if you encounter issues).

### Contributions ###

Patches, improvements and even general feedback are welcome in the form of GitHub pull requests and issue tickets.

### See Also ###

[Tools](https://github.com/harisekhon/tools) - Hadoop, NoSQL, Hive, Solr, Ambari, Web, Linux

[The Advanced Nagios Plugins Collection](https://github.com/harisekhon/nagios-plugins) - 220+ programs for Nagios monitoring your Hadoop & NoSQL clusters. Covers every Hadoop vendor's management API and every major NoSQL technology (HBase, Cassandra, MongoDB, Elasticsearch, Solr, Riak, Redis etc.) as well as traditional Linux and infrastructure.

[PyLib](https://github.com/harisekhon/pylib) - my personal python library leveraged in this repo as a submodule

[Spark Apps eg. Spark => Elasticsearch](https://github.com/harisekhon/spark-to-elasticsearch) - Scala application to index from Spark to Elasticsearch. Used to index data in Hadoop clusters or local data via Spark standalone. This started as a Scala Spark port of ```pig-text-to-elasticsearch.pig``` from this repo.
