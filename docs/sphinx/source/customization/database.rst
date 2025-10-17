Database Configuration
=======================

FLE supports checkpointing at every agent step using a SQL database. The `db_client` implements the interface for saving and loading agent outputs, environment feedbacks, game states and histories of the current trajectory.

Database Types
--------------

FLE supports multiple database backends:

**SQLite (Default)**
   Lightweight, file-based database

**PostgreSQL**
   Full-featured, server-based database

**Custom Databases**
   Extensible database interface

SQLite Configuration
--------------------

SQLite is the default database and requires minimal configuration:

.. code-block:: bash

   # Set database type
   FLE_DB_TYPE="sqlite"
   
   # Set database file path (default: .fle/data.db)
   SQLITE_DB_FILE=".fle/data.db"

SQLite is ideal for:
- Development and testing
- Single-user scenarios
- Small to medium datasets
- Quick setup and deployment

PostgreSQL Configuration
------------------------

For production use and large-scale experiments, PostgreSQL is recommended:

**Docker Setup**
   .. code-block:: bash

      docker run --name fle-postgres \
          -e POSTGRES_PASSWORD=fle123 \
          -e POSTGRES_USER=fle_user \
          -e POSTGRES_DB=fle_database \
          -p 5432:5432 \
          -d postgres:15

**Environment Variables**
   .. code-block:: bash

      # Database Configuration
      FLE_DB_TYPE="postgres"
      
      # PostgreSQL Configuration
      SKILLS_DB_HOST=localhost
      SKILLS_DB_PORT=5432
      SKILLS_DB_NAME=fle_database
      SKILLS_DB_USER=fle_user
      SKILLS_DB_PASSWORD=fle123

PostgreSQL is ideal for:
- Production deployments
- Multi-user scenarios
- Large datasets
- High-performance requirements

Database Schema
---------------

The database schema includes several key tables:

**Trajectories**
   Store complete agent trajectories

**Steps**
   Individual agent steps within trajectories

**Game States**
   Complete game state snapshots

**Agent Outputs**
   Agent-generated code and actions

**Environment Feedbacks**
   Environment responses and observations

**Metadata**
   Additional information about trajectories

Database Client
---------------

The database client provides a unified interface:

.. autoclass:: fle.commons.db_client.DatabaseClient
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
~~~~~~~~~~~

**save_trajectory(trajectory)**
   Save a complete trajectory

**load_trajectory(trajectory_id)**
   Load a trajectory by ID

**save_step(step)**
   Save an individual step

**load_steps(trajectory_id)**
   Load all steps for a trajectory

**save_game_state(state)**
   Save a game state snapshot

**load_game_state(state_id)**
   Load a game state by ID

Example Usage
-------------

**Saving a Trajectory**
   .. code-block:: python

      from fle.commons.db_client import DatabaseClient
      
      # Initialize database client
      db = DatabaseClient()
      
      # Save trajectory
      trajectory = {
          'id': 'trajectory_001',
          'agent_type': 'MyAgent',
          'task': 'iron_ore_throughput',
          'start_time': '2024-01-01T00:00:00Z',
          'end_time': '2024-01-01T01:00:00Z',
          'total_reward': 150.0,
          'success': True
      }
      
      db.save_trajectory(trajectory)

**Loading a Trajectory**
   .. code-block:: python

      # Load trajectory
      trajectory = db.load_trajectory('trajectory_001')
      print(f"Trajectory: {trajectory['id']}")
      print(f"Agent: {trajectory['agent_type']}")
      print(f"Reward: {trajectory['total_reward']}")

**Saving Steps**
   .. code-block:: python

      # Save individual step
      step = {
          'trajectory_id': 'trajectory_001',
          'step_number': 1,
          'action': 'print("Hello Factorio!")',
          'observation': {'entities': [], 'inventory': {}},
          'reward': 10.0,
          'timestamp': '2024-01-01T00:00:00Z'
      }
      
      db.save_step(step)

**Loading Steps**
   .. code-block:: python

      # Load all steps for a trajectory
      steps = db.load_steps('trajectory_001')
      for step in steps:
          print(f"Step {step['step_number']}: {step['action']}")

Database Migration
------------------

FLE includes database migration support:

**Automatic Migration**
   The system automatically migrates the database schema on startup

**Manual Migration**
   Run migrations manually when needed

**Version Control**
   Track database schema versions

Example Migration
------------------

.. code-block:: python

   from fle.commons.db_client import DatabaseClient
   
   # Initialize database client
   db = DatabaseClient()
   
   # Run migrations
   db.migrate()
   
   # Check migration status
   status = db.get_migration_status()
   print(f"Current version: {status['current_version']}")
   print(f"Latest version: {status['latest_version']}")

Performance Optimization
-----------------------

**Connection Pooling**
   Reuse database connections

**Batch Operations**
   Group multiple operations together

**Indexing**
   Optimize database queries

**Caching**
   Cache frequently accessed data

Example Optimization
-------------------

.. code-block:: python

   from fle.commons.db_client import DatabaseClient
   
   # Initialize with connection pooling
   db = DatabaseClient(
       max_connections=10,
       connection_timeout=30
   )
   
   # Batch save multiple steps
   steps = [
       {'trajectory_id': 't1', 'step_number': 1, 'action': 'action1'},
       {'trajectory_id': 't1', 'step_number': 2, 'action': 'action2'},
       {'trajectory_id': 't1', 'step_number': 3, 'action': 'action3'}
   ]
   
   db.batch_save_steps(steps)

Backup and Recovery
-------------------

**Automated Backups**
   Schedule regular database backups

**Point-in-Time Recovery**
   Restore to specific timestamps

**Data Export**
   Export data for analysis

**Data Import**
   Import data from other sources

Example Backup
--------------

.. code-block:: python

   from fle.commons.db_client import DatabaseClient
   
   # Initialize database client
   db = DatabaseClient()
   
   # Create backup
   backup_id = db.create_backup()
   print(f"Backup created: {backup_id}")
   
   # List backups
   backups = db.list_backups()
   for backup in backups:
       print(f"Backup {backup['id']}: {backup['timestamp']}")
   
   # Restore from backup
   db.restore_backup(backup_id)

Monitoring and Maintenance
--------------------------

**Performance Monitoring**
   Monitor database performance

**Health Checks**
   Verify database health

**Cleanup Operations**
   Remove old data

**Optimization**
   Optimize database performance

Example Monitoring
-----------------

.. code-block:: python

   from fle.commons.db_client import DatabaseClient
   
   # Initialize database client
   db = DatabaseClient()
   
   # Get database statistics
   stats = db.get_statistics()
   print(f"Total trajectories: {stats['trajectories']}")
   print(f"Total steps: {stats['steps']}")
   print(f"Database size: {stats['size']}")
   
   # Get performance metrics
   metrics = db.get_performance_metrics()
   print(f"Average query time: {metrics['avg_query_time']}")
   print(f"Connection count: {metrics['connection_count']}")

Troubleshooting
--------------

**Connection Issues**
   - Verify database server is running
   - Check connection parameters
   - Verify network connectivity

**Performance Issues**
   - Monitor database performance
   - Optimize queries
   - Consider connection pooling

**Data Issues**
   - Verify data integrity
   - Check for corruption
   - Run data validation

**Migration Issues**
   - Check migration status
   - Verify schema compatibility
   - Run manual migrations if needed

Best Practices
--------------

1. **Regular Backups**: Schedule automated backups
2. **Performance Monitoring**: Monitor database performance
3. **Connection Management**: Use connection pooling
4. **Data Validation**: Validate data integrity
5. **Migration Testing**: Test migrations before deployment
6. **Security**: Secure database access
7. **Documentation**: Document database configuration
