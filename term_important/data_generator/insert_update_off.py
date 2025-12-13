import json
import random
import os
from datetime import datetime
from typing import List, Dict, Any
from sklearn.model_selection import train_test_split

class UniTimeDatasetGeneratorWithUpdate:
    def __init__(self):
        self.campus = "woebegon"
        self.year = "2010"
        self.term = "Fal"
        self.date_format = "yyyy/M/d"
        self.time_format = "HHmm"
        # Using a fixed format for training consistency, or dynamic if preferred
        self.created = datetime.now().strftime("%a %b %d %H:%M:%S CEST %Y")
        self.include_exams = "none"
        self.managing_dept = "0100"
        
        # Possible data pools
        self.subjects = ["CS", "MATH", "PHYS", "CHEM", "ENGL", "DLCS", "ALG", "DRL"]
        self.course_numbers = ["101", "201", "301", "450", "106"]
        self.titles = {
            "CS": ["Intro to Programming", "Data Structures", "Algorithms", "AI Basics"],
            "MATH": ["Calculus I", "Linear Algebra", "Statistics", "Discrete Math"],
            "PHYS": ["Physics I", "Physics II", "Quantum Mechanics"],
            "CHEM": ["Chemistry I", "Organic Chemistry"],
            "ENGL": ["Composition", "Literature", "Creative Writing"],
            # "DLCS": ["Deep Learning", "Advanced AI", "Neural Networks"],
            "ALG": ["Algebra I", "Algebra II"],
            "DRL": ["Deep Renforcement Learning", "Intro to RL", "RL Agents"],
            "DLCS": ["Deep Learning CyberSecurity", "AI for Security", "Secure Deep Learning", "Deep Learning"],
            "AOL": ["Approximation", "Approximation Algorithms"],
            "CG": ["Computational Geometry", "Geometric Algorithms", "Advanced CG"],
            "DBMS": ["Database Mangament System", "Intro to Databases", "SQL", "NoSQL Databases"],
            "MVS": ["Multivariate Statistics", "Statistical Modeling"],
            "ECN": ["Econometrics", "Intro to Econometrics", "Financial Econometrics"],
            "MMD": ["Massive Data Mining", "Big Data Analytics", "Data Mining II"]
        }
        self.buildings = {"Science Hall": "SCI", "Education Center": "EDUC", "Engineering": "ENG", "Main Building": "MAIN"}
        self.room_numbers = ["101", "205", "301", "B08", "106", "103", "404"]
        self.day_patterns = ["MWF", "TTh", "MW", "T", "Th"]
        self.time_slots = [
            ("0830", "0920", 50), 
            ("0930", "1020", 50), 
            ("1030", "1120", 50),
            ("1330", "1420", 50),
            ("1430", "1520", 50)
        ]
        self.limits = [20, 25, 30, 40, 50, 100]
        self.class_types = ["Lec", "Lab", "Rec"]

    def _calculate_min_per_week(self, days: str, duration: int) -> int:
        day_count = 0
        if "M" in days: day_count += 1
        if "W" in days: day_count += 1
        if "F" in days: day_count += 1
        if "T" in days:
            # Simple heuristic for T/Th patterns
            if "Th" in days: 
                # "TTh" usually implies 2 days
                # If "T" is present, we count it. 
                pass 
            else:
                # Just "T"
                pass
        
        # Robust counting
        count = 0
        if "M" in days: count += 1
        if "T" in days: count += 1
        if "W" in days: count += 1
        if "h" in days: count += 0 # 'Th' logic handled by 'T' usually, but let's be safe
        if "F" in days: count += 1
        
        # Fix for TTh specifically if needed, or just standard length * duration
        # Assuming standard patterns:
        if days == "TTh": count = 2
        elif days == "MWF": count = 3
        elif days == "MW": count = 2
        elif days == "T": count = 1
        elif days == "Th": count = 1
        
        return count * duration

    def _time_pattern(self, days: str, duration: int) -> str:
        # e.g. "3 x 50"
        count = 0
        if days == "TTh": count = 2
        elif days == "MWF": count = 3
        elif days == "MW": count = 2
        elif days == "T": count = 1
        elif days == "Th": count = 1
        else: count = len(days) # fallback
        return f"{count} x {duration}"

    def _generate_base_details(self) -> Dict[str, Any]:
        subject = random.choice(self.subjects)
        courseNbr = random.choice(self.course_numbers)
        # Get random title for subject, fallback to generic if key missing
        title = random.choice(self.titles.get(subject, [f"{subject} Basics"]))
        
        classType = random.choice(self.class_types)
        (start, end, dur) = random.choice(self.time_slots)
        days = random.choice(self.day_patterns)
        buildingName = random.choice(list(self.buildings.keys()))
        buildingCode = self.buildings[buildingName]
        roomNbr = random.choice(self.room_numbers)
        limit = random.choice(self.limits)
        
        minPerWeek = self._calculate_min_per_week(days, dur)
        timePattern = self._time_pattern(days, dur)
        
        return {
            "subject": subject,
            "courseNbr": courseNbr,
            "title_desc": title,
            "classType": classType,
            "startTime": start,
            "endTime": end,
            "days": days,
            "duration": dur,
            "buildingName": buildingName,
            "buildingCode": buildingCode,
            "roomNbr": roomNbr,
            "limit": limit,
            "minPerWeek": minPerWeek,
            "timePattern": timePattern
        }

    def make_insert(self, d: Dict[str, Any]) -> str:
        # FIXED: Uses d['title_desc'] instead of subject_number
        return f"""<offerings campus="{self.campus}"
           year="{self.year}"
           term="{self.term}"
           dateFormat="{self.date_format}"
           timeFormat="{self.time_format}"
           created="{self.created}"
           includeExams="{self.include_exams}">

  <offering offered="true" action="insert">
    <course subject="{d['subject']}" courseNbr="{d['courseNbr']}" controlling="true" title="{d['title_desc']}"/>
    <config name="1" limit="{d['limit']}">
      <subpart type="{d['classType']}" suffix="" minPerWeek="{d['minPerWeek']}"/>
      <class type="{d['classType']}" suffix="L1" limit="{d['limit']}"
             studentScheduling="true" displayInScheduleBook="true"
             cancelled="false" managingDept="{self.managing_dept}">
        <time days="{d['days']}" startTime="{d['startTime']}" endTime="{d['endTime']}" timePattern="{d['timePattern']}"/>
        <room building="{d['buildingCode']}" roomNbr="{d['roomNbr']}"/>
      </class>
    </config>
  </offering>
</offerings>"""

    def make_update(self, old: Dict[str, Any], new: Dict[str, Any]) -> str:
        # FIXED: Uses new['title_desc'] to reflect title updates in XML
        return f"""<offerings campus="{self.campus}"
           year="{self.year}"
           term="{self.term}"
           dateFormat="{self.date_format}"
           timeFormat="{self.time_format}"
           created="{self.created}"
           includeExams="{self.include_exams}"
           incremental="true">

  <offering offered="true" action="update">
    <course subject="{old['subject']}" courseNbr="{old['courseNbr']}" controlling="true" title="{new['title_desc']}"/>
    <config name="1" limit="{new['limit']}">
      <subpart type="{new['classType']}" suffix="" minPerWeek="{new['minPerWeek']}"/>
      <class type="{new['classType']}" suffix="L1" limit="{new['limit']}"
             studentScheduling="true" displayInScheduleBook="true"
             cancelled="false" managingDept="{self.managing_dept}">
        <time days="{new['days']}" startTime="{new['startTime']}" endTime="{new['endTime']}" timePattern="{new['timePattern']}"/>
        <room building="{new['buildingCode']}" roomNbr="{new['roomNbr']}"/>
      </class>
    </config>
  </offering>
</offerings>"""

    def generate_training_samples(self, count: int) -> List[Dict[str, str]]:
        samples = []
        for _ in range(count):
            base = self._generate_base_details()
            
            # FIXED: Added "titled '{base['title_desc']}'" to the prompt
            prompt_insert_Add= (
                f"Add a new course offering: {base['subject']} {base['courseNbr']} "
                f"titled '{base['title_desc']}' as a {base['classType']} in {base['buildingName']} "
                f"room {base['roomNbr']} on {base['days']} {base['startTime']}-{base['endTime']} "
                f"with limit {base['limit']}."
            )
            xml_insert = self.make_insert(base)
            samples.append({"prompt": prompt_insert_Add, "output": xml_insert})
            
            prompt_insert_insert= (
                f"Insert a new course offering: {base['subject']} {base['courseNbr']} "
                f"titled '{base['title_desc']}' as a {base['classType']} in {base['buildingName']} "
                f"room {base['roomNbr']} on {base['days']} {base['startTime']}-{base['endTime']} "
                f"with limit {base['limit']}."
            )
            xml_insert = self.make_insert(base)
            samples.append({"prompt": prompt_insert_insert, "output": xml_insert})

            # Update Sample
            new = self._generate_base_details()
            # Keep identity (Subject + Number) same
            new['subject'] = base['subject']
            new['courseNbr'] = base['courseNbr']
            
            # FIXED: Added "to title '{new['title_desc']}'" to the update prompt
            prompt_update = (
                f"Update course {base['subject']} {base['courseNbr']} "
                f"to title '{new['title_desc']}', room {new['buildingName']} {new['roomNbr']}, "
                f"meeting {new['days']} at {new['startTime']}-{new['endTime']} "
                f"and capacity {new['limit']}."
            )
            xml_update = self.make_update(base, new)
            samples.append({"prompt": prompt_update, "output": xml_update})
            
        return samples

    def save(self, samples: List[Dict[str, str]], output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        train, temp = train_test_split(samples, test_size=0.3, random_state=42)
        val, test = train_test_split(temp, test_size=0.5, random_state=42)
        
        for fname, data in {"train.jsonl": train, "validation.jsonl": val, "test.jsonl": test}.items():
            with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                for entry in data:
                    json.dump(entry, f)
                    f.write("\n")
        print(f"✅ Generated {len(samples)} samples in '{output_dir}'")

# Usage
if __name__ == "__main__":
    gen = UniTimeDatasetGeneratorWithUpdate()
    # Generate a good amount of data for robust training
    data = gen.generate_training_samples(2000)
    gen.save(data, "./unitime_update_dataset")