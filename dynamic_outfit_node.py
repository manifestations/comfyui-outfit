import json
import random
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTFIT_DATA_DIR = DATA_DIR / "outfit"


def get_gender_folders():
    """Return a list of gender folders in the outfit data directory."""
    return [f.name for f in OUTFIT_DATA_DIR.iterdir() if f.is_dir()]


def get_body_parts(data_dir):
    """Return a list of body part names (excluding body_type and poses) for a given gender directory."""
    files = [
        f
        for f in data_dir.iterdir()
        if f.is_file()
        and f.suffix == ".json"
        and f.name not in ("body_type.json", "poses.json")
    ]
    return [f.stem for f in files]


def load_attire_options(data_dir, body_parts):
    """Load attire options for each body part from its JSON file, ignoring color/material."""
    options = {}
    for part in body_parts:
        path = data_dir / f"{part}.json"
        if not path.exists():
            options[part] = ["none", "random"]
            continue
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[DynamicOutfitNode] Error loading {path}: {e}")
                options[part] = ["none", "random"]
                continue
            attire_types = []
            for item in data.get("attire", []):
                # Only use the type, ignore color/material
                attire_types.append(item["type"])
            options[part] = ["none", "random"] + attire_types
    return options


def _load_options_from_json(file_path: Path, key: str):
    """Generic function to load a list of options from a JSON file."""
    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return ["none", "random"] + data.get(key, [])
            except Exception as e:
                print(f"[DynamicOutfitNode] Error loading {file_path}: {e}")
                return ["none", "random"]
    return ["none", "random"]


def load_makeup_options(gender: str = "female"):
    """Load makeup options from makeup.json for the specified gender, ignoring color/finish."""
    makeup_path = OUTFIT_DATA_DIR / gender / "makeup.json"
    if makeup_path.exists():
        with makeup_path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                makeup_types = []
                for item in data.get("attire", []):
                    # Only use the type, ignore color/finish
                    makeup_types.append(item["type"])
                return ["none"] + makeup_types
            except Exception as e:
                print(f"[DynamicOutfitNode] Error loading {makeup_path}: {e}")
                return ["none"]
    return ["none"]


def load_body_types(data_dir):
    """Load body types from body_type.json."""
    body_type_path = data_dir / "body_type.json"
    if body_type_path.exists():
        with body_type_path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                body_types = [item["type"] for item in data.get("attire", [])]
                return ["none", "random"] + body_types
            except Exception as e:
                print(f"[DynamicOutfitNode] Error loading {body_type_path}: {e}")
                return ["none", "random"]
    return ["none", "random"]


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

gender_folders = get_gender_folders()

for gender in gender_folders:
    gender_data_dir = OUTFIT_DATA_DIR / gender
    body_parts = get_body_parts(gender_data_dir)
    attire_options = load_attire_options(gender_data_dir, body_parts)
    # Only use gender-specific poses.json
    gender_poses_path = gender_data_dir / "poses.json"
    poses_options = _load_options_from_json(gender_poses_path, "poses")
    backgrounds_options = _load_options_from_json(
        DATA_DIR / "backgrounds.json", "backgrounds"
    )
    races_options = _load_options_from_json(DATA_DIR / "race.json", "races")
    age_groups_options = _load_options_from_json(
        DATA_DIR / "age_groups.json", "age_groups"
    )
    makeup_options = load_makeup_options(gender)
    body_types_options = load_body_types(gender_data_dir)
    class_name = f"{gender.capitalize()}OutfitNode"

    def make_node_class(
        gender,
        gender_data_dir,
        body_parts,
        attire_options,
        poses_options,
        backgrounds_options,
        races_options,
        makeup_options,
        age_groups_options,
        body_types_options,
    ):
        class DynamicOutfitNode:
            _makeup_data = None  # Cache for makeup data
            _last_seed = 0  # For increment/decrement modes

            @classmethod
            def INPUT_TYPES(cls):
                input_dict = {}
                input_dict["age_group"] = (age_groups_options, {"default": "random"})
                input_dict["character_name"] = (
                    "STRING",
                    {"default": "", "multiline": False},
                )
                input_dict["body_type"] = (body_types_options, {"default": "random"})
                for part in body_parts:
                    if part != "makeup":
                        input_dict[part] = (attire_options[part], {"default": "random"})
                input_dict["pose"] = (poses_options, {"default": "random"})
                input_dict["background"] = (backgrounds_options, {"default": "random"})
                input_dict["race"] = (races_options, {"default": "random"})
                input_dict["custom_attributes"] = (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "Enter any additional attributes not available in the dropdowns...",
                    },
                )
                input_dict["seed"] = (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 2**32 - 1,
                        "step": 1,
                        "label": "Seed",
                    },
                )
                input_dict["seed_mode"] = (
                    ["fixed", "random", "increment", "decrement"],
                    {"default": "random", "label": "Seed Mode"},
                )
                hidden_inputs = {
                    "makeup_data": ("STRING", {"default": "", "multiline": False}),
                    "_last_seed": ("INT", {"default": 0}),
                }
                return {"required": input_dict, "hidden": hidden_inputs}

            RETURN_TYPES = ("STRING", "INT")
            FUNCTION = "process"
            CATEGORY = f"\U0001f457 Outfit/{gender.capitalize()}"

            def process(self, **kwargs):
                seed = int(kwargs.get("seed", 0))
                seed_mode = kwargs.get("seed_mode", "random")
                last_seed = int(kwargs.get("_last_seed", 0))

                if seed_mode == "fixed":
                    use_seed = seed
                elif seed_mode == "random":
                    use_seed = int.from_bytes(secrets.token_bytes(4), "big")
                elif seed_mode == "increment":
                    if last_seed == 0:
                        use_seed = seed
                    else:
                        use_seed = (last_seed + 1) % (2**32)
                elif seed_mode == "decrement":
                    if last_seed == 0:
                        use_seed = seed
                    else:
                        use_seed = (last_seed - 1) % (2**32)
                else:
                    use_seed = seed

                random.seed(use_seed)
                print(
                    f"[{gender.capitalize()}OutfitNode] Using seed: {use_seed} (mode: {seed_mode})"
                )

                prompt_parts = []

                # Add character name if provided
                character_name = kwargs.get("character_name", "").strip()
                if character_name:
                    prompt_parts.append(f"Character: {character_name}")

                # Add age group with random support
                age_group = kwargs.get("age_group", "none")
                if age_group != "none":
                    if age_group == "random":
                        valid_age = [
                            opt
                            for opt in age_groups_options
                            if opt not in ["none", "random"]
                        ]
                        if valid_age:
                            age_group = random.choice(valid_age)
                    prompt_parts.append(f"Age: {age_group}")

                # Add race with random support
                race = kwargs.get("race", "none")
                if race != "none":
                    if race == "random":
                        valid_race = [
                            opt
                            for opt in races_options
                            if opt not in ["none", "random"]
                        ]
                        if valid_race:
                            race = random.choice(valid_race)
                    prompt_parts.append(f"Race: {race}")

                # Add body type with random support
                body_type = kwargs.get("body_type", "none")
                if body_type != "none":
                    if body_type == "random":
                        valid_body = [
                            opt
                            for opt in body_types_options
                            if opt not in ["none", "random"]
                        ]
                        if valid_body:
                            body_type = random.choice(valid_body)
                    prompt_parts.append(f"Body type: {body_type}")

                # Process body parts and attire
                attire_parts = []
                for part in body_parts:
                    if part != "makeup":
                        value = kwargs.get(part, "none")
                        if value not in ["none", "random"]:
                            attire_parts.append(f"{part}: {value}")
                        elif value == "random":
                            # Select random option for this part
                            options = attire_options[part]
                            valid_options = [
                                opt for opt in options if opt not in ["none", "random"]
                            ]
                            if valid_options:
                                selected = random.choice(valid_options)
                                attire_parts.append(f"{part}: {selected}")

                if attire_parts:
                    prompt_parts.append("Attire: " + ", ".join(attire_parts))

                # Process makeup for all characters (both male and female)
                makeup_parts = []
                makeup_data = kwargs.get("makeup_data", "")
                if makeup_data:
                    try:
                        makeup_items = json.loads(makeup_data)
                        for item in makeup_items:
                            if (
                                item.get("enabled", True)
                                and item.get("type")
                                and item.get("type") != "none"
                            ):
                                makeup_type = item["type"]
                                intensity = item.get("intensity", "medium")
                                color = item.get("color", "none")
                                if color and color != "none":
                                    makeup_parts.append(
                                        f"{makeup_type} ({color}, {intensity})"
                                    )
                                else:
                                    makeup_parts.append(f"{makeup_type} ({intensity})")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(
                            f"[{gender.capitalize()}OutfitNode] Error parsing makeup data: {e}"
                        )

                # Fallback: Look for individual makeup widgets (legacy support)
                if not makeup_parts:
                    # Look for makeup widgets created by the JavaScript UI
                    for key, value in kwargs.items():
                        if key.startswith("makeup_") and key.endswith("_type"):
                            # Extract the widget base name (e.g., "makeup_1" from "makeup_1_type")
                            base_name = key[:-5]  # Remove "_type"

                            # Get the corresponding intensity and enabled values
                            intensity_key = f"{base_name}_intensity"
                            enabled_key = f"{base_name}_enabled"

                            makeup_type = value
                            intensity = kwargs.get(intensity_key, "medium")
                            enabled = kwargs.get(enabled_key, True)

                            # Only include enabled makeup items that aren't "none"
                            if enabled and makeup_type and makeup_type != "none":
                                makeup_parts.append(f"{makeup_type} ({intensity})")

                if makeup_parts:
                    prompt_parts.append("Makeup: " + ", ".join(makeup_parts))

                # Add pose
                pose = kwargs.get("pose", "none")
                if pose != "none":
                    if pose == "random":
                        valid_poses = [
                            opt
                            for opt in poses_options
                            if opt not in ["none", "random"]
                        ]
                        if valid_poses:
                            pose = random.choice(valid_poses)
                    if pose != "random":
                        prompt_parts.append(f"Pose: {pose}")

                # Add background
                background = kwargs.get("background", "none")
                if background != "none":
                    if background == "random":
                        valid_backgrounds = [
                            opt
                            for opt in backgrounds_options
                            if opt not in ["none", "random"]
                        ]
                        if valid_backgrounds:
                            background = random.choice(valid_backgrounds)
                    if background != "random":
                        prompt_parts.append(f"Background: {background}")

                # Add custom attributes
                custom_attributes = kwargs.get("custom_attributes", "").strip()
                if custom_attributes:
                    prompt_parts.append(f"Additional: {custom_attributes}")

                # Join all parts with commas
                final_prompt = ", ".join(prompt_parts)

                # At the end, return the new _last_seed as a hidden output
                return (final_prompt, use_seed)

        # Register the node class in the global mappings
        DynamicOutfitNode.__name__ = class_name
        NODE_CLASS_MAPPINGS[class_name] = DynamicOutfitNode
        if gender == "female":
            NODE_DISPLAY_NAME_MAPPINGS[class_name] = "\U0001f457 Female Outfit Node"
        elif gender == "male":
            NODE_DISPLAY_NAME_MAPPINGS[class_name] = "\U0001f454 Male Outfit Node"
        else:
            NODE_DISPLAY_NAME_MAPPINGS[class_name] = (
                f"\U0001f455 {gender.capitalize()} Outfit Node"
            )
        return DynamicOutfitNode

    # Actually create and register the node class
    make_node_class(
        gender,
        gender_data_dir,
        body_parts,
        attire_options,
        poses_options,
        backgrounds_options,
        races_options,
        makeup_options,
        age_groups_options,
        body_types_options,
    )
