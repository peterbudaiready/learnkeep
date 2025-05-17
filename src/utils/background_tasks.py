import threading
from queue import Queue
from typing import Any, Callable, Dict, Optional
import time
import streamlit as st

class BackgroundTaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.queue: Queue = Queue()
        self.worker = threading.Thread(target=self._process_queue, daemon=True)
        self.worker.start()

    def _process_queue(self):
        while True:
            try:
                task_id, func, args, kwargs = self.queue.get()
                self.tasks[task_id]["status"] = "running"
                
                try:
                    result = func(*args, **kwargs)
                    self.tasks[task_id].update({
                        "status": "completed",
                        "result": result,
                        "completed_at": time.time()
                    })
                except Exception as e:
                    self.tasks[task_id].update({
                        "status": "failed",
                        "error": str(e),
                        "completed_at": time.time()
                    })
            except Exception:
                continue
            finally:
                self.queue.task_done()

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """Submit a task for background processing"""
        self.tasks[task_id] = {
            "status": "queued",
            "submitted_at": time.time(),
            "result": None,
            "error": None,
            "completed_at": None
        }
        
        self.queue.put((task_id, func, args, kwargs))
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task"""
        return self.tasks.get(task_id)

    def is_task_complete(self, task_id: str) -> bool:
        """Check if a task is complete"""
        task = self.tasks.get(task_id)
        return task is not None and task["status"] in ("completed", "failed")

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a completed task"""
        task = self.tasks.get(task_id)
        if task and task["status"] == "completed":
            return task["result"]
        return None

    def clear_completed_tasks(self, age_hours: float = 24):
        """Clear completed tasks older than age_hours"""
        current_time = time.time()
        to_remove = []
        
        for task_id, task in self.tasks.items():
            if (
                task["status"] in ("completed", "failed") and
                task["completed_at"] and
                current_time - task["completed_at"] > age_hours * 3600
            ):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]

# Initialize global task manager
task_manager = BackgroundTaskManager()

# Example usage:
# def long_running_task(param1, param2):
#     time.sleep(5)  # Simulate long operation
#     return param1 + param2
#
# task_id = task_manager.submit_task(
#     "addition_task",
#     long_running_task,
#     5, 3
# )
#
# while not task_manager.is_task_complete(task_id):
#     st.write("Processing...")
#     time.sleep(1)
#
# result = task_manager.get_task_result(task_id)
# st.write(f"Result: {result}") 