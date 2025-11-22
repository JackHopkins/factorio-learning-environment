Database Configuration
======================

FLE supports database checkpointing for long-running trajectories. The database stores agent outputs, environment feedback, game states, and histories of trajectories.

Overview
--------

The database system enables:

- **Checkpointing**: Save game state at every agent step
- **Resume Capability**: Continue trajectories from any checkpoint
- **Trajectory History**: Track complete agent interaction history
- **Analytics**: Analyze agent behavior across runs

Supported Databases
-------------------

FLE supports two database backends out of the box:

1. **SQLite** (Default): File-based, zero-configuration
2. **PostgreSQL**: Client-server, better for concurrent access

SQLite Configuration
--------------------

SQLite is the default database and requires minimal configuration.

Setup
~~~~~

1. Set the database type in ``.env``:

   .. code-block:: bash

      FLE_DB_TYPE="sqlite"

2. Configure the database file location:

   .. code-block:: bash

      SQLITE_DB_FILE=".fle/data.db"

The SQLite file will be created automatically in the specified location if it doesn't exist.

Benefits
~~~~~~~~

- **Zero Setup**: No server required
- **Portable**: Single file contains all data
- **Simple**: Easy to backup and share

Limitations
~~~~~~~~~~~

- Not suitable for concurrent writes
- Limited scalability for very large datasets
- Single-threaded access

PostgreSQL Configuration
------------------------

PostgreSQL provides better performance for large-scale experiments and concurrent access.

Setup with Docker
~~~~~~~~~~~~~~~~~

The easiest way to set up PostgreSQL is using Docker:

.. code-block:: bash

   docker run --name fle-postgres \
     -e POSTGRES_PASSWORD=fle123 \
     -e POSTGRES_USER=fle_user \
     -e POSTGRES_DB=fle_database \
     -p 5432:5432 \
     -d postgres:15

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Configure PostgreSQL in your ``.env`` file:

.. code-block:: bash

   # Database Configuration - Set to postgres to use PostgreSQL
   FLE_DB_TYPE="postgres"

   # PostgreSQL Configuration
   SKILLS_DB_HOST=localhost
   SKILLS_DB_PORT=5432
   SKILLS_DB_NAME=fle_database
   SKILLS_DB_USER=fle_user
   SKILLS_DB_PASSWORD=fle123

Manual PostgreSQL Setup
~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to install PostgreSQL manually:

1. Install PostgreSQL 15+
2. Create a database:

   .. code-block:: sql

      CREATE DATABASE fle_database;
      CREATE USER fle_user WITH PASSWORD 'fle123';
      GRANT ALL PRIVILEGES ON DATABASE fle_database TO fle_user;

3. Update ``.env`` with your connection details

Benefits
~~~~~~~~

- **Concurrent Access**: Multiple processes can write simultaneously
- **Scalability**: Handles large datasets efficiently
- **Advanced Features**: Better query optimization, indexes, etc.

Limitations
~~~~~~~~~~~

- Requires server setup and management
- More complex configuration
- Network dependency

Database Schema
---------------

The FLE database stores:

Trajectories
~~~~~~~~~~~~

- ``id``: Unique trajectory identifier
- ``task_id``: Associated task
- ``start_time``: When trajectory began
- ``end_time``: When trajectory completed
- ``status``: Current status (running, completed, failed)

Steps
~~~~~

- ``id``: Unique step identifier
- ``trajectory_id``: Parent trajectory
- ``step_number``: Sequential step number
- ``agent_code``: Code executed by agent
- ``environment_feedback``: Response from environment
- ``game_state``: Serialized game state
- ``timestamp``: When step occurred

Game States
~~~~~~~~~~~

- ``id``: Unique state identifier
- ``trajectory_id``: Associated trajectory
- ``step_id``: Associated step
- ``state_data``: Serialized game state
- ``timestamp``: When state was captured

Using the Database
------------------

Accessing the Database
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from fle.commons.db_client import get_db_client

   # Get database client (auto-detects type from .env)
   db = get_db_client()

   # Query trajectories
   trajectories = db.get_all_trajectories()

   # Get specific trajectory
   trajectory = db.get_trajectory(trajectory_id)

   # Get steps for a trajectory
   steps = db.get_trajectory_steps(trajectory_id)

Saving Checkpoints
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Save a checkpoint
   db.save_checkpoint(
       trajectory_id=trajectory_id,
       step_number=step_num,
       agent_code=code,
       environment_feedback=feedback,
       game_state=state
   )

Resuming from Checkpoint
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load checkpoint
   checkpoint = db.get_checkpoint(trajectory_id, step_number)

   # Resume environment from checkpoint
   env.load_state(checkpoint['game_state'])

   # Continue execution
   obs, reward, done, truncated, info = env.step(next_action)

Database Client API
-------------------

Core Methods
~~~~~~~~~~~~

.. code-block:: python

   # Create new trajectory
   trajectory_id = db.create_trajectory(task_id, metadata)

   # Save step
   db.save_step(trajectory_id, step_data)

   # Get trajectory
   trajectory = db.get_trajectory(trajectory_id)

   # Get all trajectories for a task
   trajectories = db.get_task_trajectories(task_id)

   # Delete trajectory
   db.delete_trajectory(trajectory_id)

Query Methods
~~~~~~~~~~~~~

.. code-block:: python

   # Get latest checkpoint
   checkpoint = db.get_latest_checkpoint(trajectory_id)

   # Get checkpoint at specific step
   checkpoint = db.get_checkpoint(trajectory_id, step_number)

   # Count steps in trajectory
   count = db.count_steps(trajectory_id)

   # Check if trajectory exists
   exists = db.trajectory_exists(trajectory_id)

Migration
---------

Switching Databases
~~~~~~~~~~~~~~~~~~~

To migrate from SQLite to PostgreSQL:

1. Export data from SQLite:

   .. code-block:: python

      from fle.commons.db_client import SQLiteClient

      sqlite_db = SQLiteClient(db_file='.fle/data.db')
      trajectories = sqlite_db.export_all()

2. Import into PostgreSQL:

   .. code-block:: python

      from fle.commons.db_client import PostgreSQLClient

      pg_db = PostgreSQLClient(
          host='localhost',
          port=5432,
          database='fle_database',
          user='fle_user',
          password='fle123'
      )
      pg_db.import_all(trajectories)

3. Update ``.env`` to use PostgreSQL

Backup and Restore
------------------

SQLite Backup
~~~~~~~~~~~~~

.. code-block:: bash

   # Simple file copy
   cp .fle/data.db .fle/data.db.backup

   # Or use SQLite command
   sqlite3 .fle/data.db ".backup '.fle/data.db.backup'"

PostgreSQL Backup
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Dump database
   pg_dump -h localhost -U fle_user fle_database > backup.sql

   # Restore database
   psql -h localhost -U fle_user fle_database < backup.sql

Performance Optimization
------------------------

SQLite Optimization
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use WAL mode for better concurrency
   db.execute("PRAGMA journal_mode=WAL")

   # Increase cache size
   db.execute("PRAGMA cache_size=-64000")  # 64MB

PostgreSQL Optimization
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   -- Create indexes for common queries
   CREATE INDEX idx_trajectory_task ON trajectories(task_id);
   CREATE INDEX idx_step_trajectory ON steps(trajectory_id);
   CREATE INDEX idx_step_timestamp ON steps(timestamp);

   -- Analyze tables
   ANALYZE trajectories;
   ANALYZE steps;

Troubleshooting
---------------

Connection Errors
~~~~~~~~~~~~~~~~~

**SQLite**:

- Verify file path exists and is writable
- Check file permissions
- Ensure parent directory exists

**PostgreSQL**:

- Verify server is running: ``docker ps`` or ``systemctl status postgresql``
- Check connection details in ``.env``
- Test connection: ``psql -h localhost -U fle_user fle_database``

Performance Issues
~~~~~~~~~~~~~~~~~~

**SQLite**:

- Enable WAL mode
- Increase cache size
- Consider switching to PostgreSQL for large datasets

**PostgreSQL**:

- Add indexes on frequently queried columns
- Tune PostgreSQL configuration (``postgresql.conf``)
- Monitor query performance with ``EXPLAIN ANALYZE``

Disk Space
~~~~~~~~~~

**SQLite**:

.. code-block:: bash

   # Check database size
   du -h .fle/data.db

   # Vacuum to reclaim space
   sqlite3 .fle/data.db "VACUUM;"

**PostgreSQL**:

.. code-block:: sql

   -- Check database size
   SELECT pg_size_pretty(pg_database_size('fle_database'));

   -- Vacuum to reclaim space
   VACUUM ANALYZE;

Best Practices
--------------

1. **Regular Backups**: Back up your database regularly, especially before major experiments
2. **Use PostgreSQL for Large Runs**: For experiments with >1000 steps, use PostgreSQL
3. **Clean Up Old Data**: Periodically remove old trajectories you no longer need
4. **Monitor Disk Space**: Keep an eye on database size, especially with SQLite
5. **Use Transactions**: Batch multiple operations in transactions for better performance

Next Steps
----------

- Review :doc:`../getting_started/quickstart` for basic usage
- See :doc:`../environment/overview` for environment context
- Check :doc:`../getting_started/troubleshooting` for common issues
