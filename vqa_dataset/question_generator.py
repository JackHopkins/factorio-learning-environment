"""
VQA question generation system for Factorio blueprints.
"""

import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from vqa_dataset.blueprint_loader import Blueprint, Entity, COMMON_ENTITY_TYPES, categorize_entity_type


@dataclass
class VQAExample:
    """Represents a single VQA example."""
    question: str
    answer: str
    question_type: str
    blueprint_name: str
    image_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class QuestionGenerator:
    """Generates VQA questions for Factorio blueprints."""
    
    def __init__(self):
        self.question_templates = self._load_question_templates()
    
    def _load_question_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load question templates organized by type."""
        return {
            'counting': [
                {
                    'template': 'How many {entity_type} are there?',
                    'answer_func': self._count_entities_by_type,
                    'requires': ['entity_type']
                },
                {
                    'template': 'How many total entities are in this blueprint?',
                    'answer_func': self._count_total_entities,
                    'requires': []
                },
                {
                    'template': 'How many different types of entities are there?',
                    'answer_func': self._count_unique_entity_types,
                    'requires': []
                },
                {
                    'template': 'How many {category} buildings are there?',
                    'answer_func': self._count_entities_by_category,
                    'requires': ['category']
                },
            ],
            'existence': [
                {
                    'template': 'Is there a {entity_type} in this blueprint?',
                    'answer_func': self._check_entity_exists,
                    'requires': ['entity_type']
                },
                {
                    'template': 'Does this blueprint contain any {category} buildings?',
                    'answer_func': self._check_category_exists,
                    'requires': ['category']
                },
                {
                    'template': 'Are there more than {threshold} {entity_type}?',
                    'answer_func': self._check_entity_threshold,
                    'requires': ['entity_type', 'threshold']
                },
            ],
            'comparison': [
                {
                    'template': 'Are there more {entity_type1} than {entity_type2}?',
                    'answer_func': self._compare_entity_counts,
                    'requires': ['entity_type1', 'entity_type2']
                },
                {
                    'template': 'Which is more common: {entity_type1} or {entity_type2}?',
                    'answer_func': self._compare_entity_prevalence,
                    'requires': ['entity_type1', 'entity_type2']
                },
            ],
            'spatial': [
                {
                    'template': 'What is the width of this blueprint?',
                    'answer_func': self._get_blueprint_width,
                    'requires': []
                },
                {
                    'template': 'What is the height of this blueprint?',
                    'answer_func': self._get_blueprint_height,
                    'requires': []
                },
                {
                    'template': 'How many entities are positioned at x-coordinate {x_coord}?',
                    'answer_func': self._count_entities_at_x,
                    'requires': ['x_coord']
                },
            ],
            'functional': [
                {
                    'template': 'What type of factory setup is this primarily for?',
                    'answer_func': self._identify_factory_type,
                    'requires': []
                },
                {
                    'template': 'Is this a mining setup?',
                    'answer_func': self._is_mining_setup,
                    'requires': []
                },
                {
                    'template': 'Is this a production setup?',
                    'answer_func': self._is_production_setup,
                    'requires': []
                },
                {
                    'template': 'Does this blueprint include power generation?',
                    'answer_func': self._has_power_generation,
                    'requires': []
                },
            ]
        }
    
    # Answer functions for different question types
    
    def _count_entities_by_type(self, blueprint: Blueprint, entity_type: str) -> str:
        """Count entities of a specific type."""
        count = len(blueprint.get_entities_by_type(entity_type))
        return str(count)
    
    def _count_total_entities(self, blueprint: Blueprint) -> str:
        """Count total entities in blueprint."""
        return str(blueprint.get_total_entity_count())
    
    def _count_unique_entity_types(self, blueprint: Blueprint) -> str:
        """Count unique entity types."""
        return str(len(blueprint.get_unique_entity_types()))
    
    def _count_entities_by_category(self, blueprint: Blueprint, category: str) -> str:
        """Count entities by category."""
        if category not in COMMON_ENTITY_TYPES:
            return "0"
        
        category_entities = COMMON_ENTITY_TYPES[category]
        count = sum(len(blueprint.get_entities_by_type(entity_type)) 
                   for entity_type in category_entities)
        return str(count)
    
    def _check_entity_exists(self, blueprint: Blueprint, entity_type: str) -> str:
        """Check if entity type exists."""
        return "yes" if blueprint.has_entity_type(entity_type) else "no"
    
    def _check_category_exists(self, blueprint: Blueprint, category: str) -> str:
        """Check if any entities from category exist."""
        if category not in COMMON_ENTITY_TYPES:
            return "no"
        
        category_entities = COMMON_ENTITY_TYPES[category]
        has_any = any(blueprint.has_entity_type(entity_type) 
                     for entity_type in category_entities)
        return "yes" if has_any else "no"
    
    def _check_entity_threshold(self, blueprint: Blueprint, entity_type: str, threshold: int) -> str:
        """Check if entity count exceeds threshold."""
        count = len(blueprint.get_entities_by_type(entity_type))
        return "yes" if count > threshold else "no"
    
    def _compare_entity_counts(self, blueprint: Blueprint, entity_type1: str, entity_type2: str) -> str:
        """Compare counts of two entity types."""
        count1 = len(blueprint.get_entities_by_type(entity_type1))
        count2 = len(blueprint.get_entities_by_type(entity_type2))
        return "yes" if count1 > count2 else "no"
    
    def _compare_entity_prevalence(self, blueprint: Blueprint, entity_type1: str, entity_type2: str) -> str:
        """Return which entity type is more common."""
        count1 = len(blueprint.get_entities_by_type(entity_type1))
        count2 = len(blueprint.get_entities_by_type(entity_type2))
        
        if count1 > count2:
            return entity_type1.replace('-', ' ')
        elif count2 > count1:
            return entity_type2.replace('-', ' ')
        else:
            return "equal"
    
    def _get_blueprint_width(self, blueprint: Blueprint) -> str:
        """Get blueprint width."""
        width, _ = blueprint.get_dimensions()
        return str(int(round(width)))
    
    def _get_blueprint_height(self, blueprint: Blueprint) -> str:
        """Get blueprint height."""
        _, height = blueprint.get_dimensions()
        return str(int(round(height)))
    
    def _count_entities_at_x(self, blueprint: Blueprint, x_coord: float) -> str:
        """Count entities at specific x coordinate."""
        count = sum(1 for entity in blueprint.entities 
                   if abs(entity.position['x'] - x_coord) < 0.5)
        return str(count)
    
    def _identify_factory_type(self, blueprint: Blueprint) -> str:
        """Identify the primary factory type."""
        entity_counts = blueprint.get_entity_counts()
        
        # Check for different setup types
        if any(entity in entity_counts for entity in COMMON_ENTITY_TYPES['mining']):
            return "mining"
        elif any(entity in entity_counts for entity in COMMON_ENTITY_TYPES['production']):
            return "production"
        elif any(entity in entity_counts for entity in COMMON_ENTITY_TYPES['defense']):
            return "defense"
        elif any(entity in entity_counts for entity in COMMON_ENTITY_TYPES['power']):
            return "power generation"
        elif any(entity in entity_counts for entity in COMMON_ENTITY_TYPES['chemical']):
            return "chemical processing"
        else:
            return "general purpose"
    
    def _is_mining_setup(self, blueprint: Blueprint) -> str:
        """Check if this is primarily a mining setup."""
        has_mining = any(blueprint.has_entity_type(entity_type) 
                        for entity_type in COMMON_ENTITY_TYPES['mining'])
        return "yes" if has_mining else "no"
    
    def _is_production_setup(self, blueprint: Blueprint) -> str:
        """Check if this is primarily a production setup."""
        has_production = any(blueprint.has_entity_type(entity_type) 
                           for entity_type in COMMON_ENTITY_TYPES['production'])
        return "yes" if has_production else "no"
    
    def _has_power_generation(self, blueprint: Blueprint) -> str:
        """Check if blueprint includes power generation."""
        has_power = any(blueprint.has_entity_type(entity_type) 
                       for entity_type in COMMON_ENTITY_TYPES['power'])
        return "yes" if has_power else "no"
    
    def generate_questions_for_blueprint(
        self, 
        blueprint: Blueprint, 
        blueprint_name: str,
        num_questions_per_type: int = 2,
        question_types: Optional[List[str]] = None
    ) -> List[VQAExample]:
        """Generate VQA questions for a single blueprint."""
        if question_types is None:
            question_types = list(self.question_templates.keys())
        
        questions = []
        entity_types = blueprint.get_unique_entity_types()
        entity_counts = blueprint.get_entity_counts()
        
        for question_type in question_types:
            templates = self.question_templates[question_type]
            
            # Generate multiple questions of this type
            for _ in range(num_questions_per_type):
                template = random.choice(templates)
                
                try:
                    # Prepare template parameters
                    params = {}
                    
                    if 'entity_type' in template['requires']:
                        if not entity_types:
                            continue
                        params['entity_type'] = random.choice(entity_types)
                    
                    if 'entity_type1' in template['requires']:
                        if len(entity_types) < 2:
                            continue
                        params['entity_type1'] = random.choice(entity_types)
                        remaining_types = [t for t in entity_types if t != params['entity_type1']]
                        params['entity_type2'] = random.choice(remaining_types)
                    
                    if 'category' in template['requires']:
                        available_categories = [cat for cat in COMMON_ENTITY_TYPES.keys()
                                              if any(blueprint.has_entity_type(et) 
                                                   for et in COMMON_ENTITY_TYPES[cat])]
                        if not available_categories:
                            continue
                        params['category'] = random.choice(available_categories)
                    
                    if 'threshold' in template['requires']:
                        entity_type = params.get('entity_type')
                        if entity_type:
                            max_count = entity_counts.get(entity_type, 0)
                            params['threshold'] = random.randint(0, max(1, max_count + 2))
                    
                    if 'x_coord' in template['requires']:
                        min_x, _, max_x, _ = blueprint.get_bounding_box()
                        params['x_coord'] = random.uniform(min_x, max_x)
                    
                    # Generate question and answer
                    question = template['template'].format(**params)
                    answer = template['answer_func'](blueprint, **params)
                    
                    vqa_example = VQAExample(
                        question=question,
                        answer=answer,
                        question_type=question_type,
                        blueprint_name=blueprint_name,
                        metadata={
                            'template_params': params,
                            'entity_count': blueprint.get_total_entity_count(),
                            'unique_types': len(entity_types)
                        }
                    )
                    
                    questions.append(vqa_example)
                    
                except Exception as e:
                    print(f"Failed to generate question: {e}")
                    continue
        
        return questions
    
    def generate_questions_batch(
        self, 
        blueprints: Dict[str, Blueprint],
        num_questions_per_blueprint: int = 10,
        question_types: Optional[List[str]] = None
    ) -> List[VQAExample]:
        """Generate VQA questions for multiple blueprints."""
        all_questions = []
        
        questions_per_type = max(1, num_questions_per_blueprint // len(self.question_templates))
        
        for blueprint_name, blueprint in blueprints.items():
            try:
                questions = self.generate_questions_for_blueprint(
                    blueprint, 
                    blueprint_name,
                    num_questions_per_type=questions_per_type,
                    question_types=question_types
                )
                all_questions.extend(questions)
            except Exception as e:
                print(f"Failed to generate questions for {blueprint_name}: {e}")
        
        return all_questions
    
    def get_question_statistics(self, questions: List[VQAExample]) -> Dict[str, Any]:
        """Get statistics about generated questions."""
        if not questions:
            return {}
        
        question_types = Counter(q.question_type for q in questions)
        answer_lengths = Counter(len(q.answer.split()) for q in questions)
        unique_answers = len(set(q.answer for q in questions))
        
        return {
            'total_questions': len(questions),
            'question_types': dict(question_types),
            'unique_answers': unique_answers,
            'avg_answer_length': sum(len(q.answer.split()) for q in questions) / len(questions),
            'answer_length_distribution': dict(answer_lengths)
        }


# Utility functions for question filtering and validation
def filter_questions_by_complexity(
    questions: List[VQAExample], 
    min_answer_length: int = 1,
    max_answer_length: int = 10
) -> List[VQAExample]:
    """Filter questions by answer complexity."""
    return [
        q for q in questions 
        if min_answer_length <= len(q.answer.split()) <= max_answer_length
    ]


def balance_question_types(
    questions: List[VQAExample], 
    max_per_type: int = 100
) -> List[VQAExample]:
    """Balance questions across different types."""
    type_counts = Counter(q.question_type for q in questions)
    balanced = []
    
    for question_type in type_counts:
        type_questions = [q for q in questions if q.question_type == question_type]
        balanced.extend(random.sample(type_questions, min(len(type_questions), max_per_type)))
    
    return balanced


# Example usage
if __name__ == "__main__":
    from vqa_dataset.blueprint_loader import BlueprintLoader
    
    # Load blueprints
    loader = BlueprintLoader("fle/agents/data/blueprints_to_policies/blueprints")
    blueprints = loader.load_all_blueprints(['example', 'other'])
    blueprints = loader.filter_blueprints_by_complexity(blueprints, max_entities=100)
    
    print(f"Loaded {len(blueprints)} blueprints")
    
    # Generate questions
    generator = QuestionGenerator()
    questions = generator.generate_questions_batch(blueprints, num_questions_per_blueprint=5)
    
    print(f"Generated {len(questions)} questions")
    
    # Show statistics
    stats = generator.get_question_statistics(questions)
    print("Question statistics:", stats)
    
    # Show some example questions
    print("\nExample questions:")
    for i, q in enumerate(questions[:10]):
        print(f"{i+1}. Q: {q.question}")
        print(f"   A: {q.answer}")
        print(f"   Type: {q.question_type}")
        print()