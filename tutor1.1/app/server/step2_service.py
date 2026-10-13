import os
import re
import unicodedata

import config
from text_utils import parse_subjects_value


def slugify_folder_name(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "unknown"


def ensure_step2_folder_structure(country, subjects):
    country_name = str(country or "").strip() or "unknown-country"
    country_slug = slugify_folder_name(country_name)
    created_paths = []

    curriculum_country_root = os.path.join(config.CURRICULA_ROOT, country_slug)
    amendments_country_root = os.path.join(config.AMENDMENTS_ROOT, country_slug)
    for root_path in (curriculum_country_root, amendments_country_root):
        os.makedirs(root_path, exist_ok=True)
        created_paths.append(root_path)

    normalized_subjects = parse_subjects_value(subjects)
    if not normalized_subjects:
        normalized_subjects = ["unknown-subject"]

    subject_paths = []
    for subject in normalized_subjects:
        subject_slug = slugify_folder_name(subject)
        curriculum_subject_path = os.path.join(curriculum_country_root, subject_slug)
        amendments_subject_path = os.path.join(amendments_country_root, subject_slug)
        os.makedirs(curriculum_subject_path, exist_ok=True)
        os.makedirs(amendments_subject_path, exist_ok=True)
        subject_paths.append(
            {
                "subject": subject,
                "slug": subject_slug,
                "curriculum": curriculum_subject_path,
                "amendments": amendments_subject_path,
            }
        )
        created_paths.extend([curriculum_subject_path, amendments_subject_path])

    return {
        "country": country_name,
        "countrySlug": country_slug,
        "curriculumRoot": curriculum_country_root,
        "amendmentsRoot": amendments_country_root,
        "subjects": subject_paths,
        "createdPaths": created_paths,
    }


def save_uploaded_files_to_folder(file_items, target_folder):
    saved_files = []
    os.makedirs(target_folder, exist_ok=True)

    for file_item in file_items:
        filename = os.path.basename(getattr(file_item, "filename", "") or "")
        if not filename:
            continue
        target_path = os.path.join(target_folder, filename)
        counter = 1
        base_name, extension = os.path.splitext(filename)
        while os.path.exists(target_path):
            target_path = os.path.join(target_folder, f"{base_name}-{counter}{extension}")
            counter += 1
        with open(target_path, "wb") as output_file:
            output_file.write(file_item.file.read())
        saved_files.append({
            "filename": os.path.basename(target_path),
            "path": target_path,
        })

    return saved_files
