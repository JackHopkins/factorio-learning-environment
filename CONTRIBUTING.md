## Contributing Guidelines

We welcome contributions to the Factorio Learning Environment! Here's how you can help:

### Getting Started

1. Fork the repository and clone your fork
2. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Commit your changes with clear, descriptive commit messages
5. Push to your fork and submit a pull request

### Code Style and Standards

- Follow PEP 8 style guide for Python code
- Use type hints for all function parameters and return values
- Document new functions and classes using docstrings
- Add unit tests for new functionality in `tests/`
- Keep line length to 100 characters or less
- Use meaningful variable and function names

### Pull Request Process

1. Ensure your code passes all existing tests
2. Add tests for new functionality
3. Update documentation as needed
4. Link any related issues in your pull request description
5. Wait for review from maintainers

### Adding New Tools

When adding new tools to the environment:

1. Follow the structure outlined in the [Tool Documentation](README.md#tool-documentation) section
2. Include comprehensive docstrings and type hints
3. Add examples in the tool's `agent.md` file
4. Create appropriate test cases
5. Update the core tools table in the main README if applicable

### Creating New Agents

When implementing new agents:

1. Create a new file in the `agents/` directory
2. Inherit from `AgentABC` base class
3. Implement required methods:
   - `step(conversation: Conversation, response: Response) -> Policy`
   - `end(conversation: Conversation, completion: CompletionState) -> None`
4. Document your agent's:
   - Architecture and key components
   - Required dependencies
   - Prompt engineering approach (if applicable)
   - Performance characteristics
5. Add evaluation results to `eval/` directory
6. Provide baseline performance metrics on standard tasks (128 steps) and open-world scenarios (3,000 steps).

Key considerations:
- Handle context management for long episodes
- Implement proper error handling and recovery
- Document any assumptions about the environment
- Consider resource usage and optimization
- Test with both lab-play and open-play scenarios

### Creating New Tasks

When adding new evaluation tasks:

1. Create a new file in `eval/tasks/task_definitions/`
2. Inherit from `TaskABC` base class
3. Define task components:
   - Initial conditions and environment setup
   - Success criteria and metrics
   - Time limits and resource constraints
   - Scoring mechanism
4. Implement required methods:
   - `setup(instance: FactorioInstance)`: Initialize task environment
   - `verify(self, score: float, step: int, instance: FactorioInstance, step_statistics: Dict) -> bool:`: Verify task completion based on score and step count at step N.
5. Document the task:
   - Purpose and learning objectives
   - Expected agent behavior
   - Failure modes and edge cases
   - Performance benchmarks
6. Add test cases in `eval/tasks/tests/`

Best practices:
- Design clear, measurable success criteria
- Include progressive difficulty levels
- Provide example solutions
- Document required tools and resources
- Consider computational requirements
- Test with multiple agent types

### Bug Reports and Feature Requests

- Use the GitHub issue tracker
- Provide detailed descriptions and steps to reproduce for bugs
- Include example code or scenarios when possible
- Label issues appropriately
- Check existing issues before creating new ones

### Code Review Process

All submissions require review. We use GitHub pull requests for this purpose:

1. Maintainers will review your code for:
   - Functionality
   - Code style
   - Test coverage
   - Documentation
2. Changes may be requested before merging
3. Once approved, maintainers will merge your PR

### Community Guidelines

- Be respectful and inclusive
- Help others in the community
- Provide constructive feedback
- Follow the code of conduct
- Build an enormous factory