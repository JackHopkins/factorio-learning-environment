# Factorio Learning Environment Tutorial

## Introduction

Welcome to the Factorio Learning Environment (FLE), a powerful platform designed to help you experiment with Factorio factory designs through a version-controlled approach. This environment allows you to write Python code that interacts with Factorio, manage different versions of your designs, and learn from both your successes and failures.

## Core Concepts

### The Learning Environment

The Factorio Learning Environment provides a standardized interface for interacting with Factorio game servers. This system allows you to:

- Connect to running Factorio server instances
- Execute Python code to manipulate the game state
- Render the factory state as images
- Track and manage different versions of your factory designs
- Access detailed information about recipes, entities, and resources

### Version Control System

One of the most powerful features of the FLE is its built-in version control system (VCS). Similar to Git for software development, it enables you to:

- Create checkpoints (commits) of your factory state
- Tag specific states for easy reference
- Restore previous states when a design doesn't work
- View the history of your changes
- Analyze the code that led to specific results

This system is crucial for learning and experimentation as it allows you to:
- Try multiple approaches to solving problems
- Backtrack when a design doesn't work
- Compare different strategies
- Build upon successful iterations
- Learn from failures without losing progress

## Python Code Execution in Factorio

The core of the FLE is the ability to write and execute Python code that interacts with the Factorio game state. Here's what you should understand about code execution:

### Code Structure Overview

Your Python code will typically handle:
- Finding resource patches like iron ore, copper ore, coal, etc.
- Moving to locations before interacting with the world
- Placing entities like mining drills, furnaces, and assembling machines
- Setting up connections between entities with belts, inserters, and power poles
- Ensuring entities have the required fuel or resources
- Crafting items before placing entities that require them
- Setting up automation with proper ratios between machines
- Creating self-sustaining systems that don't require manual intervention

### Code Introspection

The FLE provides powerful code introspection tools that allow you to:

- Explore existing code patterns and implementations
- Learn from provided examples in the codebase
- Understand the structure and organization of the environment
- Find specific functions and their documentation
- Search for relevant code that solves similar problems to what you're facing

You can access this code through the Unix-like tools provided in the environment (explained below), allowing you to learn from existing implementations as you build your solutions.

## Workflow Strategies

### Experimental Approach

1. **Start Small**: Begin with simple, focused experiments
2. **Commit Regularly**: Create checkpoints after meaningful changes
3. **Learn Incrementally**: Add complexity gradually, validating each step
4. **When Stuck, Backtrack**: Use version control to restore working states
5. **Analyze Failures**: Understand what went wrong before trying again
6. **Build on Success**: Use successful patterns as foundations for more complex designs
7. **Human Feedback**: If you are stuck, ask for human feedback!

### Version Control Strategy

1. **Create Initial Checkpoint**: Always commit your starting state
2. **Use Descriptive Tags**: Give commits clear names that describe what they represent
3. **Checkpoint Before Risk**: Commit before trying experimental approaches
4. **Compare Alternatives**: Create branches of development to test different strategies
5. **Restore and Retry**: Don't be afraid to restore previous states and try again
6. **Document Insights**: Include what you learned in commit messages

### Code Development Strategy

1. **Explore the Codebase**: Use the Unix-like tools to understand existing patterns
2. **Start with Fundamentals**: Build basic resource gathering before complex automation
3. **Modular Approach**: Build functions for common tasks
4. **Validate Each Step**: Test components individually before integration
5. **Handle Edge Cases**: Include error checks and fallbacks
6. **Iterate and Refine**: Continuously improve designs based on performance

## Tips for Effective Learning

1. **Explore Existing Code**: Use tools like `grep`, `cat`, and `find` to discover how existing functionality is implemented.

2. **Read the Documentation**: Use `manual` and `schema` to understand available API functionality for executing Python.

3. **Analyze Working Examples**: When you succeed with a design, tag it using `commit`, and use `view_code` to review the pattern associated with a tag for future reference.

4. **Learn from Failures**: When a design doesn't work, use version control to analyze what went wrong.

5. **Incremental Development**: Build your solution step by step, validating each component.

6. **Visualize Regularly**: Use `render` to see how your factory is developing at different stages.

7. **Experiment Freely**: The version control system allows you to try bold approaches without fear of losing progress.

## Common Challenges

### Resource Management

- Finding and efficiently mining resources
- Processing raw materials into intermediate products
- Balancing production and consumption rates

### Factory Design

- Creating efficient layouts for machines
- Managing space constraints
- Ensuring proper connections between components

### Automation

- Setting up self-sustaining systems
- Creating reliable belt and inserter networks
- Building power infrastructure

### Optimization

- Improving throughput of production lines
- Reducing resource waste
- Scaling production to meet demand

## Getting Started

When you begin, it is wise to:
1. Read a complete list of prototypes
2. Read the API schema to understand the object model of Factorio 
3. Read the manuals of all tools to see how they work
4. Write utility functions to combine the tools in useful ways
5. Test your code by running it, and rolling back on failure to address the root issue before proceeding