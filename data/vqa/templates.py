from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any

class TemplateManager:
    """Manages Jinja2 templates for VQA tasks."""
    
    def __init__(self, base_path: Path = None):
        if base_path is None:
            base_path = Path(__file__).parent / "tasks"
        
        self.base_path = base_path
        self.environments = {}
        self._init_environments()
    
    def _init_environments(self):
        """Initialize Jinja2 environments for each task type."""
        task_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]
        
        for task_dir in task_dirs:
            templates_dir = task_dir / "templates"
            if templates_dir.exists():
                env = Environment(
                    loader=FileSystemLoader(str(templates_dir)),
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                self.environments[task_dir.name] = env
    
    def render(self, task_type: str, template_name: str, **kwargs) -> str:
        """Render a template with the given parameters."""
        if task_type not in self.environments:
            raise ValueError(f"Unknown task type: {task_type}")
        
        env = self.environments[task_type]
        template = env.get_template(f"{template_name}.jinja2")
        return template.render(**kwargs)
    
    def get_available_tasks(self) -> list:
        """Get list of available task types."""
        return list(self.environments.keys())
    
    def get_available_templates(self, task_type: str) -> list:
        """Get list of available templates for a task type."""
        if task_type not in self.environments:
            return []
        
        templates_dir = self.base_path / task_type / "templates"
        return [f.stem for f in templates_dir.glob("*.jinja2")]

# Global template manager instance
template_manager = TemplateManager()

# Convenience functions for backward compatibility
def render_template(task_type: str, template_name: str, **kwargs) -> str:
    """Render a template using the global template manager."""
    return template_manager.render(task_type, template_name, **kwargs)

# Template shortcuts for each task type
class Templates:
    """Template shortcuts for easy access."""
    
    @staticmethod
    def blueprint_title_purpose(blueprint: Dict[str, Any]) -> str:
        return render_template("contrastive_alignment", "blueprint_title_purpose", blueprint=blueprint)
    
    @staticmethod
    def contrastive_matching(options: list) -> str:
        return render_template("contrastive_alignment", "contrastive_matching", options=options)
    
    @staticmethod
    def denoising_question(position: Dict[str, Any], entity_name: str) -> str:
        return render_template("denoising", "question_generation", position=position, entity_name=entity_name)
    
    @staticmethod
    def denoising_validation(modified_blueprint: Dict[str, Any], question: str) -> str:
        return render_template("denoising", "validation", modified_blueprint=modified_blueprint, question=question)
    
    @staticmethod
    def spatial_context_question(removed_entity: Dict[str, Any], removed_position: Dict[str, Any], 
                                nearby_entities: list, nearest_entity_name: str) -> str:
        return render_template("spatial_reasoning", "spatial_context_question", 
                             removed_entity=removed_entity, removed_position=removed_position,
                             nearby_entities=nearby_entities, nearest_entity_name=nearest_entity_name)
    
    @staticmethod
    def spatial_question(blueprint: Dict[str, Any], question: str) -> str:
        return render_template("spatial_reasoning", "spatial_question", blueprint=blueprint, question=question)
    
    @staticmethod
    def entity_name_position(blueprint: Dict[str, Any], question: str) -> str:
        return render_template("basic", "entity_name_position", blueprint=blueprint, question=question)
    
    @staticmethod
    def state_prediction(factory_state: Dict[str, Any], question: str) -> str:
        return render_template("state_prediction", "state_prediction", factory_state=factory_state, question=question)
    
    @staticmethod
    def action_prediction(previous_actions: list, blueprint: Dict[str, Any]) -> str:
        return render_template("action_prediction", "action_prediction", 
                             previous_actions=previous_actions, blueprint=blueprint)
    
    @staticmethod
    def productivity_planning(factory_state: Dict[str, Any], entity1_name: str, entity1_pos: Dict[str, Any],
                             entity2_name: str, entity2_pos: Dict[str, Any]) -> str:
        return render_template("productivity_planning", "productivity_planning",
                             factory_state=factory_state, entity1_name=entity1_name, entity1_pos=entity1_pos,
                             entity2_name=entity2_name, entity2_pos=entity2_pos)