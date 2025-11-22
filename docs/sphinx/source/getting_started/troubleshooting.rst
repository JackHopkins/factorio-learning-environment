Troubleshooting
===============

This page addresses common issues you may encounter when using FLE.

Common Issues
-------------

"No valid programs found for version X"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: You see this message during initialization.

**Solution**: This is normal during initialization. The system will start generating programs shortly. No action needed.

Database Connection Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Errors connecting to the database when running evaluations.

**Solution**:

1. Verify your database configuration in the ``.env`` file
2. Ensure the database exists
3. For SQLite: Check that the directory for the database file exists
4. For PostgreSQL: Verify the database server is running

API Key Errors
~~~~~~~~~~~~~~

**Symptom**: Authentication errors when running agent evaluations.

**Solution**:

1. Run the API key setup script:

   .. code-block:: bash

      python fle/eval/infra/setup_api_keys.py

2. Verify your API keys are correctly set in the ``.env`` file
3. Check that you're using the correct provider (OpenAI, Anthropic, etc.)

Docker Issues
~~~~~~~~~~~~~

**Symptom**: Permission denied or Docker connection errors.

**Solution**:

1. Ensure Docker is installed and running
2. Verify your user has permission to run Docker without sudo:

   .. code-block:: bash

      sudo usermod -aG docker $USER

3. Log out and log back in for the group change to take effect
4. Test Docker access:

   .. code-block:: bash

      docker ps

Connection Issues
~~~~~~~~~~~~~~~~~

**Symptom**: Cannot connect to Factorio server.

**Solution**:

1. Make sure the Factorio server is running:

   .. code-block:: bash

      fle cluster start

2. Check that ports are properly configured
3. Verify Docker containers are running:

   .. code-block:: bash

      docker ps

4. Check Docker logs for errors:

   .. code-block:: bash

      docker logs <container_id>

Environment Creation Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``gym.make()`` fails with connection errors.

**Solution**:

1. Ensure Factorio containers are running
2. Check that the cluster setup is working
3. Verify network connectivity

No Environments Found
~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``list_available_environments()`` returns an empty list.

**Solution**:

1. Check that the task definitions directory exists
2. Verify JSON files in ``fle/eval/tasks/task_definitions/`` are valid
3. Check file permissions
4. Ensure you're running from the correct directory

Import Errors
~~~~~~~~~~~~~

**Symptom**: ``ModuleNotFoundError`` or import errors.

**Solution**:

1. Ensure you're running from the correct directory
2. Check that all dependencies are installed:

   .. code-block:: bash

      pip install factorio-learning-environment[eval]

3. Verify the Python path includes the project root
4. Try reinstalling the package:

   .. code-block:: bash

      pip install --force-reinstall factorio-learning-environment

Space Age DLC Issues
~~~~~~~~~~~~~~~~~~~~

**Symptom**: Factorio client is on version 2.x instead of 1.1.110.

**Solution**:

1. Open Steam library
2. Right-click Factorio → Properties
3. Navigate to DLC section
4. **Uncheck Space Age DLC** (this forces the 2.x branch)
5. Go to Betas tab
6. Select version ``1.1.110``

Testing Your Installation
--------------------------

Run the test suite to verify everything is working:

.. code-block:: bash

   # Test the gym registry
   python fle/env/tests/gym_env/test_registry.py

   # List available environments
   python fle/env/gym_env/example_usage.py --list

   # Run with detailed output
   python fle/env/gym_env/example_usage.py --detail

Getting Help
------------

If you continue to experience issues:

1. Check the `GitHub Issues <https://github.com/JackHopkins/factorio-learning-environment/issues>`_
2. Join the `Discord (#factorio-learning-env) <https://discord.gg/zKaV2skewa>`_
3. Review the :doc:`../project_structure` to understand the codebase layout

Debugging Tips
--------------

Enable Verbose Logging
~~~~~~~~~~~~~~~~~~~~~~~

Set environment variables for more detailed output:

.. code-block:: bash

   export FLE_LOG_LEVEL=DEBUG

Check Docker Logs
~~~~~~~~~~~~~~~~~

View logs from Factorio containers:

.. code-block:: bash

   # List running containers
   docker ps

   # View logs for a specific container
   docker logs <container_id>

   # Follow logs in real-time
   docker logs -f <container_id>

Verify Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check that your ``.env`` file is properly loaded:

.. code-block:: python

   import os
   from dotenv import load_dotenv

   load_dotenv()
   print(os.getenv('OPENAI_API_KEY'))  # Should show your API key (masked)
   print(os.getenv('FLE_DB_TYPE'))     # Should show sqlite or postgres
