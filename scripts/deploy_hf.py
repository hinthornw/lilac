"""Deploy to a huggingface space.

Usage:
  poetry run python -m scripts.deploy_hf

"""
import os
import shutil
import subprocess
from typing import Optional

import click
import yaml
from huggingface_hub import HfApi

from lilac.concepts.db_concept import DiskConceptDB, get_concept_output_dir
from lilac.config import CONFIG_FILENAME, DatasetConfig
from lilac.env import data_path, env
from lilac.project import PROJECT_CONFIG_FILENAME
from lilac.sources.huggingface_source import HuggingFaceSource
from lilac.utils import get_dataset_output_dir, get_hf_dataset_repo_id, get_lilac_cache_dir, to_yaml

HF_SPACE_DIR = '.hf_spaces'
PY_DIST_DIR = 'dist'


@click.command()
@click.option(
  '--hf_username', help='The huggingface username to use to authenticate for the space.', type=str)
@click.option(
  '--hf_space',
  help='The huggingface space. Defaults to env.HF_STAGING_DEMO_REPO. '
  'Should be formatted like `SPACE_ORG/SPACE_NAME`.',
  type=str)
@click.option('--dataset', help='The name of a dataset to upload', type=str, multiple=True)
@click.option(
  '--concept',
  help='The name of a concept to upload. By default all lilac/ concepts are uploaded.',
  type=str,
  multiple=True)
@click.option(
  '--skip_build',
  help='Skip building the web server TypeScript. '
  'Useful to speed up the build if you are only changing python or data.',
  type=bool,
  is_flag=True,
  default=False)
@click.option(
  '--skip_cache',
  help='Skip uploading the cache files from .cache/lilac which contain cached concept pkl models.',
  type=bool,
  is_flag=True,
  default=False)
@click.option(
  '--data_dir',
  help='The data directory to use for the demo. Defaults to `env.DATA_DIR`.',
  type=str,
  default=data_path())
@click.option(
  '--make_datasets_public',
  help='When true, sets the huggingface datasets uploaded to public. Defaults to false.',
  is_flag=True,
  default=False)
@click.option(
  '--use_pip',
  help='When true, uses the public pip package. When false, builds and uses a local wheel.',
  is_flag=True,
  default=False)
@click.option(
  '--disable_google_analytics',
  help='When true, disables Google Analytics.',
  is_flag=True,
  default=False)
def deploy_hf_command(hf_username: Optional[str], hf_space: Optional[str], dataset: list[str],
                      concept: list[str], skip_build: bool, skip_cache: bool,
                      data_dir: Optional[str], make_datasets_public: bool, use_pip: bool,
                      disable_google_analytics: bool) -> None:
  """Generate the huggingface space app."""
  deploy_hf(hf_username, hf_space, dataset, concept, skip_build, skip_cache, data_dir,
            make_datasets_public, use_pip, disable_google_analytics)


def deploy_hf(hf_username: Optional[str], hf_space: Optional[str], datasets: list[str],
              concepts: list[str], skip_build: bool, skip_cache: bool, data_dir: Optional[str],
              make_datasets_public: bool, use_pip: bool, disable_google_analytics: bool) -> None:
  """Generate the huggingface space app."""
  data_dir = data_dir or data_path()

  hf_username = hf_username or env('HF_USERNAME')
  if not hf_username:
    raise ValueError('Must specify --hf_username or set env.HF_USERNAME')

  hf_space = hf_space or env('HF_STAGING_DEMO_REPO')
  if not hf_space:
    raise ValueError('Must specify --hf_space or set env.HF_STAGING_DEMO_REPO')

  # Build the web server Svelte & TypeScript.
  if not use_pip and not skip_build:
    print('Building webserver...')
    run('./scripts/build_server_prod.sh')

  hf_api = HfApi()

  # Unconditionally remove dist. dist is unconditionally uploaded so it is empty when using
  # the public package.
  if os.path.exists(PY_DIST_DIR):
    shutil.rmtree(PY_DIST_DIR)
  os.makedirs(PY_DIST_DIR, exist_ok=True)

  # Make an empty readme in py_dist_dir.
  with open(os.path.join(PY_DIST_DIR, 'README.md'), 'w') as f:
    f.write('This directory is used for locally built whl files.\n'
            'We write a README.md to ensure an empty folder is uploaded when there is no whl.')

  # Build the wheel for pip.
  if not use_pip:
    # We have to change the version to a dev version so that the huggingface demo does not try to
    # install the public pip package.
    current_lilac_version = run('poetry version -s').stdout.strip()
    # Bump the version temporarily so that the install uses this pip.
    version_parts = current_lilac_version.split('.')
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    temp_new_version = '.'.join(version_parts)

    run(f'poetry version "{temp_new_version}"')
    run('poetry build -f wheel')
    run(f'poetry version "{current_lilac_version}"')

  lilac_hf_datasets: list[str] = []

  # Upload datasets.
  hf_space_org, hf_space_name = hf_space.split('/')
  # Upload datasets to HuggingFace. We do this after uploading code to avoid clobbering the data
  # directory.
  # NOTE(nsthorat): This currently doesn't write to persistent storage directly.
  for d in datasets:
    namespace, name = d.split('/')
    dataset_repo_id = get_hf_dataset_repo_id(hf_space_org, hf_space_name, namespace, name)

    print(f'Uploading to HuggingFace repo https://huggingface.co/datasets/{dataset_repo_id}\n')

    hf_api.create_repo(
      dataset_repo_id, repo_type='dataset', private=not make_datasets_public, exist_ok=True)
    dataset_output_dir = get_dataset_output_dir(data_dir, namespace, name)
    hf_api.upload_folder(
      folder_path=dataset_output_dir,
      path_in_repo=os.path.join(namespace, name),
      repo_id=dataset_repo_id,
      repo_type='dataset',
      # Delete all data on the server.
      delete_patterns='*')

    config_filepath = os.path.join(dataset_output_dir, CONFIG_FILENAME)
    with open(config_filepath) as f:
      dataset_config_yaml = f.read()

    dataset_link = ''
    dataset_config = DatasetConfig.parse_obj(yaml.safe_load(dataset_config_yaml))
    if isinstance(dataset_config.source, HuggingFaceSource):
      dataset_link = f'https://huggingface.co/datasets/{dataset_config.source.dataset_name}'

    readme = (
      ('This dataset is generated by [Lilac](http://lilacml.com) for a HuggingFace Space: '
       f'[huggingface.co/spaces/{hf_space_org}/{hf_space_name}]'
       f'(https://huggingface.co/spaces/{hf_space_org}/{hf_space_name}).\n\n' +
       (f'Original dataset: [{dataset_link}]({dataset_link})\n\n' if dataset_link != '' else '') +
       'Lilac dataset config:\n'
       f'```{dataset_config_yaml}```\n\n').encode())
    hf_api.upload_file(
      path_or_fileobj=readme,
      path_in_repo='README.md',
      repo_id=dataset_repo_id,
      repo_type='dataset',
    )

    lilac_hf_datasets.append(dataset_repo_id)

  hf_space_dir = os.path.join(data_dir, HF_SPACE_DIR)

  run(f'mkdir -p {hf_space_dir}')

  # Clone the HuggingFace spaces repo.
  print(f'Cloning {hf_space} to {hf_space_dir}...')
  repo_basedir = os.path.join(hf_space_dir, hf_space)
  run(f'rm -rf {repo_basedir}')
  run(f'git clone https://{hf_username}@huggingface.co/spaces/{hf_space} {repo_basedir} '
      '--depth 1 --quiet --no-checkout')

  # Clear out the repo.
  run(f'rm -rf {repo_basedir}/*')

  print('Copying root files...')
  # Copy a subset of root files.
  copy_files = [
    '.dockerignore', '.env', 'Dockerfile', 'LICENSE', 'docker_start.sh', 'docker_start.py'
  ]
  for copy_file in copy_files:
    shutil.copyfile(copy_file, os.path.join(repo_basedir, copy_file))

  # Copy the lilac.yml
  repo_data_dir = os.path.join(repo_basedir, 'data')
  if not os.path.exists(repo_data_dir):
    os.makedirs(repo_data_dir)
  shutil.copyfile(
    os.path.join(data_dir, PROJECT_CONFIG_FILENAME),
    os.path.join(repo_data_dir, PROJECT_CONFIG_FILENAME))

  # Create an .env.local to set HF-specific flags.
  with open(f'{repo_basedir}/.env.demo', 'w') as f:
    f.write(f"""LILAC_DATA_PATH='/data'
HF_HOME=/data/.huggingface
TRANSFORMERS_CACHE=/data/.cache
XDG_CACHE_HOME=/data/.cache
{'GOOGLE_ANALYTICS_ENABLED=true' if not disable_google_analytics else ''}
""")

  # Create a .gitignore to avoid uploading unnecessary files.
  with open(f'{repo_basedir}/.gitignore', 'w') as f:
    f.write("""__pycache__/
**/*.pyc
**/*.pyo
**/*.pyd
**/*_test.py
""")

  # Create the huggingface README.
  with open(f'{repo_basedir}/README.md', 'w') as f:
    config = {
      'title': 'Lilac',
      'emoji': '🌷',
      'colorFrom': 'purple',
      'colorTo': 'purple',
      'sdk': 'docker',
      'app_port': 5432,
      'datasets': [d for d in lilac_hf_datasets],
    }
    f.write(f'---\n{to_yaml(config)}\n---')

  run(f"""pushd {repo_basedir} > /dev/null && \
      git add . && \
      (git diff-index --quiet --cached HEAD ||
        (git commit -a -m "Push" --quiet && git push)) && \
      popd > /dev/null""")

  print('Uploading wheel files...')
  # Upload the wheel files.
  hf_api.upload_folder(
    folder_path=PY_DIST_DIR,
    path_in_repo=PY_DIST_DIR,
    repo_id=hf_space,
    repo_type='space',
    # Delete all data on the server.
    delete_patterns='*')

  print('Uploading cache files...')
  # Upload the cache files.
  cache_dir = get_lilac_cache_dir(data_dir)
  if not skip_cache and os.path.exists(cache_dir):
    hf_api.upload_folder(
      folder_path=cache_dir,
      path_in_repo=get_lilac_cache_dir('data'),
      repo_id=hf_space,
      repo_type='space',
      # Delete all data on the server.
      delete_patterns='*')

  # Upload concepts.
  print('Uploading concepts...')
  disk_concepts = [
    # Remove lilac concepts as they're checked in, and not in the
    f'{c.namespace}/{c.name}' for c in DiskConceptDB(data_dir).list() if c.namespace != 'lilac'
  ]
  for c in concepts:
    if c not in disk_concepts:
      raise ValueError(f'Concept "{c}" not found in disk concepts: {disk_concepts}')

  for c in concepts:
    namespace, name = c.split('/')
    hf_api.upload_folder(
      folder_path=get_concept_output_dir(data_dir, namespace, name),
      path_in_repo=get_concept_output_dir('data', namespace, name),
      repo_id=hf_space,
      repo_type='space',
      # Delete all data on the server.
      delete_patterns='*')


def run(cmd: str) -> subprocess.CompletedProcess[str]:
  """Run a command and return the result."""
  return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)


if __name__ == '__main__':
  deploy_hf_command()
