"""
Learning Store for User Edits
Stores user filename edits and provides similar examples for LLM
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Storage file path
LEARNING_STORE_PATH = os.getenv("LEARNING_STORE_PATH", "learning_store.json")


class LearningStore:
    """Store and retrieve user filename edits for LLM learning"""
    
    def __init__(self, store_path: str = LEARNING_STORE_PATH):
        self.store_path = store_path
        self._ensure_store_exists()
    
    def _ensure_store_exists(self):
        """Create store file if it doesn't exist"""
        if not os.path.exists(self.store_path):
            with open(self.store_path, 'w') as f:
                json.dump({"edits": []}, f, indent=2)
    
    def _load_store(self) -> Dict[str, Any]:
        """Load the learning store from file"""
        try:
            with open(self.store_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"edits": []}
    
    def _save_store(self, data: Dict[str, Any]):
        """Save the learning store to file"""
        with open(self.store_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_edit(
        self,
        original_filename: str,
        edited_filename: str,
        fields: Dict[str, Optional[str]],
        text_sample: str = ""
    ):
        """
        Add a user edit to the learning store
        
        Args:
            original_filename: Original suggested filename
            edited_filename: User-edited filename
            fields: Extracted fields (doc_type, issuer, date_iso, etc.)
            text_sample: Sample of document text (first 500 chars for matching)
        """
        store = self._load_store()
        
        edit_entry = {
            "timestamp": datetime.now().isoformat(),
            "original_filename": original_filename,
            "edited_filename": edited_filename,
            "fields": {
                "doc_type": fields.get("doc_type"),
                "issuer": fields.get("issuer"),
                "date_iso": fields.get("date_iso"),
                "asx_code": fields.get("asx_code"),
                "account_last4": fields.get("account_last4")
            },
            "text_sample": text_sample[:500] if text_sample else "",  # Store first 500 chars for matching
        }
        
        store["edits"].append(edit_entry)
        
        # Keep only last 1000 edits to prevent file from growing too large
        if len(store["edits"]) > 1000:
            store["edits"] = store["edits"][-1000:]
        
        self._save_store(store)
        print(f"Learning store: Added edit example (total: {len(store['edits'])})")
    
    def find_similar_edits(
        self,
        fields: Dict[str, Optional[str]],
        text_sample: str = "",
        max_examples: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find similar edits based on document fields and text
        
        Args:
            fields: Current document fields
            text_sample: Sample of document text
            max_examples: Maximum number of examples to return
            
        Returns:
            List of similar edit examples
        """
        store = self._load_store()
        edits = store.get("edits", [])
        
        if not edits:
            return []
        
        # Score each edit for similarity
        scored_edits = []
        current_doc_type = (fields.get("doc_type") or "").lower()
        current_issuer = (fields.get("issuer") or "").lower()
        
        for edit in edits:
            score = 0
            edit_fields = edit.get("fields", {})
            
            # Exact doc_type match: +10 points
            if edit_fields.get("doc_type", "").lower() == current_doc_type:
                score += 10
            
            # Issuer similarity: +5 points for exact match, +2 for partial match
            edit_issuer = (edit_fields.get("issuer") or "").lower()
            if edit_issuer and current_issuer:
                if edit_issuer == current_issuer:
                    score += 5
                elif edit_issuer in current_issuer or current_issuer in edit_issuer:
                    score += 2
            
            # Text similarity: check if key terms match
            edit_text = (edit.get("text_sample") or "").lower()
            current_text = text_sample[:500].lower() if text_sample else ""
            
            # Count common words (excluding common stop words)
            if edit_text and current_text:
                edit_words = set(edit_text.split())
                current_words = set(current_text.split())
                common_words = edit_words & current_words
                # Remove common stop words
                stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
                common_words = common_words - stop_words
                if len(common_words) > 0:
                    score += min(len(common_words), 5)  # Max 5 points for text similarity
            
            if score > 0:
                scored_edits.append((score, edit))
        
        # Sort by score (highest first) and return top examples
        scored_edits.sort(key=lambda x: x[0], reverse=True)
        
        # Return top examples (without the score)
        return [edit for _, edit in scored_edits[:max_examples]]
    
    def get_all_edits(self) -> List[Dict[str, Any]]:
        """Get all stored edits (for debugging/admin)"""
        store = self._load_store()
        return store.get("edits", [])
    
    def clear_edits(self):
        """Clear all stored edits"""
        self._save_store({"edits": []})
        print("Learning store: Cleared all edits")


# Global instance
_learning_store: Optional[LearningStore] = None


def get_learning_store() -> LearningStore:
    """Get or create the global learning store instance"""
    global _learning_store
    if _learning_store is None:
        _learning_store = LearningStore()
    return _learning_store

