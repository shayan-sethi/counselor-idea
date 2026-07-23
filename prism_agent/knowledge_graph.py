import os
import json

class KnowledgeGraph:
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to the data directory relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "requirements_db.json")
        
        self.db_path = db_path
        self.requirements = {}
        self.load_database()

    def load_database(self):
        """Loads requirements data from JSON file."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Requirements database not found at: {self.db_path}")
        
        with open(self.db_path, "r") as f:
            self.requirements = json.load(f)

    def get_course_or_exam(self, node_id):
        """Fetches a course or exam by its ID."""
        return self.requirements.get(node_id)

    def get_all_targets(self):
        """Returns all courses and exams in the graph."""
        return list(self.requirements.values())

    def get_targets_by_track(self, track):
        """Filters targets by track (India, UK, US)."""
        return [node for node in self.requirements.values() if node.get("track") == track]

    def get_prerequisites(self, node_id):
        """Retrieves subject prerequisites for a specific node."""
        target = self.get_course_or_exam(node_id)
        if target:
            return target.get("subject_prerequisites", [])
        return []

    def get_deadlines(self, node_id):
        """Retrieves deadlines for a specific node."""
        target = self.get_course_or_exam(node_id)
        if target:
            return target.get("deadlines", [])
        return []

    def get_admission_tests(self, node_id):
        """Retrieves admission test codes for a specific node."""
        target = self.get_course_or_exam(node_id)
        if target:
            return target.get("admission_tests", [])
        return []

    def get_grade_prerequisites(self, node_id):
        """Retrieves minimum grade rules for a specific node."""
        target = self.get_course_or_exam(node_id)
        if target:
            return target.get("grade_prerequisites", [])
        return []
