import json
import random
import os
import time
from typing import List, Dict, Any, Tuple
from sklearn.model_selection import train_test_split

class NLPToXMLPreferencesGenerator:
    """
    Generates a dataset of NLP prompts and their corresponding UniTime preferences.xml completions.
    Matches the specific XML schema provided by the user (Fall 2010, Woebegon campus).
    """

    ### 1. Initialization and Data Pools ###
    def __init__(self):
        # --- Fixed values from the target XML format ---
        self.campus = "woebegon"
        self.year = "2010"
        self.term = "Fal"
        self.date_format = "yyyy/M/d"
        self.time_format = "HHmm"
        
        # --- Data Pools (derived from your XML snippet) ---
        self.pref_levels = {
            "P": "preferred",
            "2": "strongly preferred",
            "1": "weakly preferred",
            "0": "neutral",
            "-1": "discouraged",
            "-2": "prohibited",
            "R": "required"
        }
        
        # Departments
        self.dept_codes = ["0100", "0101", "0102"]
        
        # Rooms (Location + Preference Level for Depts)
        self.rooms = ["EDUC 101", "THTR 101", "EDUC 106", "EDUC 102", "MALL", "SCI 205", "EDUC 108", "EDUC 107"]
        
        # Instructors (ID, First, Middle, Last, Dept)
        # Added middle names to match your snippet's "JOHN WILLIAM SMITH" style
        self.instructors = [
            ("100", "JOE", "", "DOE", "0101"),
            ("101", "GEORGE", "", "NEWMAN", "0101"),
            ("102", "JOHN", "WILLIAM", "SMITH", "0101"),
            ("103", "SARAH", "", "JENKINS", "0102")
        ]
        
        # Room Features
        self.features = ["Comp", "ThtrSeat", "Projector", "Whiteboard", "Audio"]
        
        # Buildings
        self.buildings = ["EDUC", "THTR", "MALL", "SCI", "LART"]
        
        # Days (R = Thursday)
        self.days = ["M", "T", "W", "R", "F"]
        
        # Time Slots (start, stop)
        self.time_slots = [
            ("0730", "0830"), ("0930", "1430"), ("0830", "1830"),
            ("0930", "1330"), ("1630", "1830")
        ]
        
        # Subparts (Courses)
        self.subparts = [
            ("ALG", "101", "Lec"), ("BIOL", "101", "Lab"), ("BIOL", "101", "Lec"),
            ("C S", "101", "Lab"), ("CHM", "101", "Lec"), ("ECON", "101", "Lec")
        ]
        
        # Time Patterns
        self.patterns = ["3 x 50", "2 x 75", "1 x 100", "1 x 150", "5 x 100"]
        
        # Room Groups
        self.groups = ["Classroom", "Comp Labs", "Biol Labs"]

        # --- List of all generator functions ---
        # We duplicate the 'complex' generator to make it appear more often (higher weight)
        self.generators = [
            self.generate_dept_room_pref,
            self.generate_instructor_time_pref,
            self.generate_instructor_feature_pref,
            self.generate_instructor_building_pref,
            self.generate_subpart_group_pref,
            self.generate_subpart_time_pref,
            self.generate_complex_instructor_profile, # Weight 1
            self.generate_complex_instructor_profile, # Weight 2
        ]

    ### 2. Helper Methods ###

    def _get_random_level(self) -> Tuple[str, str]:
        """Picks a random preference level code and its name."""
        level_code = random.choice(list(self.pref_levels.keys()))
        level_name = self.pref_levels[level_code]
        return level_code, level_name

    def _get_timestamp(self) -> str:
        """Generates a dynamic timestamp matching the XML format: Sat Dec 06 20:19:04 CET 2025"""
        return time.strftime("%a %b %d %H:%M:%S %Z %Y")

    def _wrap_xml(self, content: str) -> str:
        """Wraps the generated XML snippet in the root <preferences> tag."""
        # Using the dynamic timestamp here
        timestamp = self._get_timestamp()
        
        xml = f'''<preferences term="{self.term}" year="{self.year}" campus="{self.campus}" dateFormat="{self.date_format}" timeFormat="{self.time_format}" created="{timestamp}">
{content}
</preferences>'''
        # Clean up whitespace to match the clean look of your snippet
        return "\n".join(line for line in xml.splitlines() if line.strip())

    ### 3. Specific Preference Generators ###

    def generate_dept_room_pref(self) -> Dict[str, str]:
        """Generates a sample for a department's room preference."""
        dept = random.choice(self.dept_codes)
        room = random.choice(self.rooms)
        level_code, level_name = self._get_random_level()

        prompt = f"For department {dept}, set the preference for room {room} to {level_name}."
        
        xml_content = f'''<department code="{dept}">
<roomPref location="{room}" level="{level_code}"/>
</department>'''
        
        return {
            "type": "DepartmentRoomPref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_instructor_time_pref(self) -> Dict[str, str]:
        """Generates a sample for an instructor's time preference."""
        inst_id, f_name, m_name, l_name, dept = random.choice(self.instructors)
        full_name = f"{f_name} {m_name} {l_name}".replace("  ", " ") # Handle empty middle name
        
        # Create a "main" preference for the prompt
        main_day = random.choice(self.days)
        main_start, main_stop = random.choice(self.time_slots)
        main_level, main_level_name = self._get_random_level()
        
        prompt = f"Instructor {full_name} ({dept}) requires {main_day} {main_start}-{main_stop} to be {main_level_name}."

        # Generate the XML list
        # Note: Your snippet nests <pref> inside <timePref level="R">
        prefs_xml = ""
        # Main pref
        prefs_xml += f'<pref level="{main_level}" day="{main_day}" start="{main_start}" stop="{main_stop}"/>'
        
        # Add random noise (other days) to simulate a real schedule
        for _ in range(random.randint(1, 3)):
            day = random.choice(self.days)
            start, stop = random.choice(self.time_slots)
            level, _ = self._get_random_level()
            if day != main_day: # simple duplicate avoidance
                prefs_xml += f'\n<pref level="{level}" day="{day}" start="{start}" stop="{stop}"/>'

        # Construct XML with attribute handling
        # Only add middleName attribute if it exists
        if m_name:
            inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" middleName="{m_name}" lastName="{l_name}" department="{dept}">'
        else:
            inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" lastName="{l_name}" department="{dept}">'

        xml_content = f'''{inst_tag}
<timePref level="R">
{prefs_xml}
</timePref>
</instructor>'''
        
        return {
            "type": "InstructorTimePref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_instructor_feature_pref(self) -> Dict[str, str]:
        """Generates a sample for an instructor's room feature preference."""
        inst_id, f_name, m_name, l_name, dept = random.choice(self.instructors)
        full_name = f"{f_name} {m_name} {l_name}".replace("  ", " ")
        
        feature = random.choice(self.features)
        level_code, level_name = self._get_random_level()

        prompt = f"Instructor {full_name} has a {level_name} preference for the '{feature}' feature."
        
        inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" lastName="{l_name}" department="{dept}">'
        if m_name: inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" middleName="{m_name}" lastName="{l_name}" department="{dept}">'

        xml_content = f'''{inst_tag}
<featurePref feature="{feature}" level="{level_code}"/>
</instructor>'''
        
        return {
            "type": "InstructorFeaturePref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_instructor_building_pref(self) -> Dict[str, str]:
        """Generates a sample for an instructor's building preference."""
        inst_id, f_name, m_name, l_name, dept = random.choice(self.instructors)
        full_name = f"{f_name} {m_name} {l_name}".replace("  ", " ")

        building = random.choice(self.buildings)
        level_code, level_name = self._get_random_level()

        prompt = f"Set a building preference for {full_name}: {building} is {level_name}."
        
        inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" lastName="{l_name}" department="{dept}">'
        if m_name: inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" middleName="{m_name}" lastName="{l_name}" department="{dept}">'

        xml_content = f'''{inst_tag}
<buildingPref building="{building}" level="{level_code}"/>
</instructor>'''
        
        return {
            "type": "InstructorBuildingPref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_complex_instructor_profile(self) -> Dict[str, str]:
        """
        Generates a sample where ONE instructor has MULTIPLE preference types at once.
        This matches the density of your provided XML (e.g. JOE DOE having features + time).
        """
        inst_id, f_name, m_name, l_name, dept = random.choice(self.instructors)
        full_name = f"{f_name} {m_name} {l_name}".replace("  ", " ")

        # 1. Feature Pref
        feature = random.choice(self.features)
        f_level_c, f_level_n = self._get_random_level()
        feat_xml = f'<featurePref feature="{feature}" level="{f_level_c}"/>'

        # 2. Time Pref
        day = random.choice(self.days)
        start, stop = random.choice(self.time_slots)
        t_level_c, t_level_n = self._get_random_level()
        time_xml = f'<timePref level="R">\n<pref level="{t_level_c}" day="{day}" start="{start}" stop="{stop}"/>\n</timePref>'

        # 3. Building Pref
        building = random.choice(self.buildings)
        b_level_c, b_level_n = self._get_random_level()
        build_xml = f'<buildingPref building="{building}" level="{b_level_c}"/>'

        # Combined Prompt
        prompt = (f"Update preferences for {full_name} ({dept}): "
                  f"They require the '{feature}' feature ({f_level_n}), "
                  f"schedule {day} {start}-{stop} as {t_level_n}, "
                  f"and mark building {building} as {b_level_n}.")

        # Combined XML
        inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" lastName="{l_name}" department="{dept}">'
        if m_name: inst_tag = f'<instructor externalId="{inst_id}" firstName="{f_name}" middleName="{m_name}" lastName="{l_name}" department="{dept}">'

        xml_content = f'''{inst_tag}
{feat_xml}
{time_xml}
{build_xml}
</instructor>'''

        return {
            "type": "ComplexInstructorProfile",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_subpart_group_pref(self) -> Dict[str, str]:
        """Generates a sample for a course subpart's room group preference."""
        subject, course, type_ = random.choice(self.subparts)
        group = random.choice(self.groups)
        level_code, level_name = self._get_random_level()
        
        prompt = f"The {subject} {course} {type_} subpart has a {level_name} preference for '{group}' rooms."
        
        xml_content = f'''<subpart subject="{subject}" course="{course}" type="{type_}">
<groupPref group="{group}" level="{level_code}"/>
</subpart>'''
        
        return {
            "type": "SubpartGroupPref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    def generate_subpart_time_pref(self) -> Dict[str, str]:
        """Generates a sample for a course subpart's time pattern."""
        subject, course, type_ = random.choice(self.subparts)
        pattern = random.choice(self.patterns)
        level_code, level_name = self._get_random_level()

        prompt = f"For {subject} {course} {type_}, set the time pattern {pattern} to {level_name}."
            
        xml_content = f'''<subpart subject="{subject}" course="{course}" type="{type_}">
<timePref pattern="{pattern}" level="{level_code}"/>
</subpart>'''
        
        return {
            "type": "SubpartTimePref",
            "prompt": prompt,
            "output": self._wrap_xml(xml_content)
        }

    ### 4. Main Dataset Creation and Saving Logic ###

    def generate_training_samples(self, count: int) -> List[Dict[str, str]]:
        samples = []
        for _ in range(count):
            generator_func = random.choice(self.generators)
            sample = generator_func()
            samples.append(sample)
        return samples

    def save_dataset_to_jsonl(self, samples: List[Dict[str, str]], output_dir="/home/sysadm/Music/unitime/unitime_nlp/data/Preferences_dataset"):
        os.makedirs(output_dir, exist_ok=True)
        
        train, temp = train_test_split(samples, test_size=0.3, random_state=42)
        val, test = train_test_split(temp, test_size=0.5, random_state=42)
        
        splits = {"train.jsonl": train, "validation.jsonl": val, "test.jsonl": test}
        
        for filename, data in splits.items():
            path = os.path.join(output_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                for entry in data:
                    json.dump(entry, f)
                    f.write('\n')
            print(f"Saved {len(data)} samples to {path}")

# --- Execution ---
if __name__ == "__main__":
    generator = NLPToXMLPreferencesGenerator()
    
    print("Generating 2500 training samples...")
    # Increased count slightly to accommodate new complex types
    all_samples = generator.generate_training_samples(count=2500)
    
    print("\nSplitting and saving the dataset...")
    generator.save_dataset_to_jsonl(all_samples)
    
    print("\n" + "="*80)
    print("Verification: Showing 1 Complex Sample (Matches your XML structure)")
    print("="*80)
    
    # Filter for a complex one to show the user
    complex_samples = [s for s in all_samples if s['type'] == 'ComplexInstructorProfile']
    if complex_samples:
        s = complex_samples[0]
        print(f"[PROMPT]:\n{s['prompt']}")
        print(f"\n[OUTPUT]:\n{s['output']}")
    print("="*80)