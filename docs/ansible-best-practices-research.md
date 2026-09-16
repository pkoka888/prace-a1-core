# Ansible Best Practices Research Report
## Django + PostgreSQL + nginx + systemd deployment stack

**Research date**: 2026-09-17  
**Sources consulted**: Official Ansible documentation (docs.ansible.com), Ansible for DevOps (Jeff Geerling), YPCrumble/ansible-django-stack, ansible/molecule, ansible-lint source, Ansible community docs

---

## Table of Contents

1. [Ansible Project Structure Best Practices](#1-ansible-project-structure-best-practices)
2. [Ansible Idempotent Deployment Patterns](#2-ansible-idempotent-deployment-patterns)
3. [Ansible with Django Deployments](#3-ansible-with-django-deployments)
4. [Ansible Testing and Validation](#4-ansible-testing-and-validation)
5. [Ansible vs Alternatives](#5-ansible-vs-alternatives)
6. [Real-World Examples](#6-real-world-examples)

---

## 1. Ansible Project Structure Best Practices

### 1.1 Directory Layout

**Practice**: Use a conventional directory layout separating inventory, playbooks, roles, and variables.

**Recommended layout for this project**:

```
ansible/
  ansible.cfg
  inventories/
    production/
      hosts                  # inventory file
      group_vars/
        all.yml              # shared defaults
        webservers.yml        # web-tier variables
      host_vars/
        web01.example.com.yml
    staging/
      hosts
      group_vars/
        all.yml
  playbooks/
    site.yml                  # master playbook
    webservers.yml            # web tier entry point
    database.yml              # db tier entry point
  roles/
    common/
      tasks/main.yml
      handlers/main.yml
      templates/
      files/
      vars/main.yml
      defaults/main.yml
      meta/main.yml
    nginx/
    gunicorn/
    postgresql/
    django_app/
    python_venv/
  library/                    # optional custom modules
  filter_plugins/             # optional custom filters
  requirements.yml            # Galaxy dependencies
```

**Why it matters for this project**: The Django + PostgreSQL + nginx + systemd stack has clear functional boundaries (web, app, db). Roles let you package each layer independently and reuse them across environments. Separate inventory per environment prevents accidental production changes.

**Authoritative sources**:
- [Ansible Sample Setup](https://docs.ansible.com/projects/ansible/latest/tips_tricks/sample_setup.html) — canonical reference layout
- [Ansible Best Practices (user guide)](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html) (legacy, still widely cited)
- [Roles documentation](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_reuse_roles.html)

**Recommended implementation**:
- Use `inventories/` with subdirectories per environment (production, staging), each containing its own `hosts`, `group_vars/`, and `host_vars/`.
- Use `playbooks/` for entry-point playbooks that call roles.
- Use `roles/` for all reusable logic, one role per concern (e.g., `nginx`, `postgresql`, `django_app`, `gunicorn`).
- Put `ansible.cfg` at the project root with `roles_path = ./roles` and `inventory = ./inventories/production/hosts`.

---

### 1.2 Variable Precedence and Best Practices

**Practice**: Define each variable in one place and use Ansible's documented precedence intentionally.

**Key precedence tiers (least to greatest)**:
1. Role defaults (`roles/x/defaults/main.yml`) — safe to override anywhere
2. Inventory group_vars/all
3. Inventory group_vars/<group>
4. Inventory host_vars/<host>
5. Playbook vars, vars_files, vars_prompt
6. Role vars (`roles/x/vars/main.yml`) — hard to override, use for role-internal invariants
7. Extra vars (`-e`) — always win

**Why it matters for this project**: Django settings like `SECRET_KEY`, database credentials, and domain names need to be overridable per-environment without editing role internals. Secrets must be vaulted; app config must be overridable via `group_vars`.

**Authoritative sources**:
- [Using variables — Ansible docs](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html#variable-precedence-where-should-i-put-a-variable)
- [Inventory variable merging](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html#how-variables-are-merged)

**Recommended implementation**:
- Role defaults: safe defaults (ports, package names, path conventions).
- `group_vars/all`: non-sensitive shared config (e.g., `project_name`, `domain_name`, `python_version`).
- `group_vars/vault`: encrypted secrets file (see §1.4 below).
- `host_vars/<host>`: only host-specific overrides (e.g., IP, SSH port).

---

### 1.3 When to Use Roles vs Flat Playbooks

**Practice**: Use roles for any reusable or complex logic; use playbooks as thin orchestration layers that call roles.

**Rule of thumb**:
- If you might run the same logic against a different host group, or in a different playbook → **role**.
- If the logic is a one-off sequence tied to a single play → inline tasks in the playbook are acceptable for small scripts.
- For this project (Django stack), **all functional concerns should be roles**: `postgresql`, `nginx`, `gunicorn`, `django_app`, `python_venv`.

**Why it matters**: Roles have a defined internal structure (tasks, handlers, templates, vars, defaults, meta), support role argument specs, can declare dependencies, and are testable in isolation with Molecule.

**Authoritative sources**:
- [Roles — Ansible docs](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
- [Jeff Geerling, Ansible for DevOps](https://www.ansiblefordevops.com/)

**Recommended implementation**:
```
site.yml:
  - import_playbook: webservers.yml
  - import_playbook: database.yml

webservers.yml:
  - hosts: webservers
    roles:
      - common
      - python_venv
      - postgresql_client
      - django_app
      - gunicorn
      - nginx
```

---

### 1.4 Secrets Management

**Practice**: Use Ansible Vault with the "vars + vault" pattern for group-level secrets.

**Recommended approach** (from Ansible tips and tricks):
1. Create `group_vars/<group>/vars` (unencrypted, contains variable names and non-sensitive values).
2. Create `group_vars/<group>/vault` (encrypted, contains `vault_` prefixed secret values).
3. In `vars`, reference vault variables: `db_password: "{{ vault_db_password }}"`.
4. Encrypt the `vault` file: `ansible-vault encrypt group_vars/<group>/vault`.

**For multi-environment setups**: Use vault IDs (`--vault-id prod@prompt`, `--vault-id staging@staging-vault-pass`).

**Why it matters**: Django `SECRET_KEY`, database passwords, and any API keys must never appear in plaintext in version control. The vars+vault pattern keeps variable names greppable while keeping values encrypted.

**Authoritative sources**:
- [Ansible Vault — encrypted variables and files](https://docs.ansible.com/projects/ansible/latest/vault_guide/vault_using_encrypted_content.html)
- [Ansible tips — keep vaulted variables safely visible](https://docs.ansible.com/projects/ansible/latest/tips_tricks/ansible_tips_tricks.html#keep-vaulted-variables-safely-visible)

**Recommended implementation**:
```
group_vars/webservers/vars:
  django_secret_key: "{{ vault_django_secret_key }}"
  db_password: "{{ vault_db_password }}"

group_vars/webservers/vault:  # encrypted
  vault_django_secret_key: "xYz..."
  vault_db_password: "s3cret..."
```

---

## 2. Ansible Idempotent Deployment Patterns

### 2.1 systemd Service Management

**Practice**: Use `ansible.builtin.systemd_service` with explicit `state`, `enabled`, and `daemon_reload`.

```yaml
- name: Ensure gunicorn service is running and enabled
  ansible.builtin.systemd_service:
    name: gunicorn
    state: started
    enabled: true
    daemon_reload: true   # pick up unit file changes
```

**Why it matters**: Without `daemon_reload: true`, systemd won't see a changed unit file and the service won't restart. Without `enabled: true`, the service won't start on boot. Using the native module (not `service`) ensures systemd-specific behavior.

**Authoritative sources**:
- [ansible.builtin.systemd_service module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/systemd_service_module.html)

---

### 2.2 nginx Configuration (Template + Handler)

**Practice**: Render nginx site config from a Jinja2 template, notify a handler to reload nginx only when changed.

```yaml
- name: Deploy nginx site configuration
  ansible.builtin.template:
    src: nginx-site.conf.j2
    dest: /etc/nginx/sites-available/{{ project_name }}
    owner: root
    group: root
    mode: '0644'
  notify: Reload nginx

handlers:
  - name: Reload nginx
    ansible.builtin.systemd_service:
      name: nginx
      state: reloaded
```

**Why it matters**: Handlers run only when a task reports `changed`, preventing unnecessary reloads. The `template` module checks content hash; identical content means no change = no reload. Use `validate: 'nginx -t -c %s'` on the template module for syntax checking before deploy.

**Authoritative sources**:
- [Handlers — Ansible docs](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_handlers.html)
- [template module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html)

---

### 2.3 Python Virtualenv and Package Installation

**Practice**: Use `ansible.builtin.pip` with `virtualenv` parameter to install into a venv; use `requirements` for reproducible installs.

```yaml
- name: Ensure virtualenv exists
  ansible.builtin.pip:
    virtualenv: "{{ venv_path }}"
    python_version: "{{ python_version }}"
    state: present

- name: Install application requirements
  ansible.builtin.pip:
    virtualenv: "{{ venv_path }}"
    requirements: "{{ project_path }}/requirements.txt"
    extra_args: "{{ pip_extra_args | default(omit) }}"
  notify: Restart gunicorn
```

**Why it matters**: Installing directly into the virtualenv ensures isolation from the system Python. Pinning requirements in `requirements.txt` makes deploys reproducible. The pip module is idempotent — it only installs missing or changed packages.

**Authoritative sources**:
- [ansible.builtin.pip module (community.general)](https://docs.ansible.com/projects/ansible/latest/collections/community/general/pip_module.html)
- [YPCrumble/ansible-django-stack — setup_django_app.yml](https://github.com/YPCrumble/ansible-django-stack/blob/master/roles/web/tasks/setup_django_app.yml)

---

### 2.4 Database Migrations

**Practice**: Run migrations as a separate tagged task with explicit failure handling; do not run them on every deploy automatically.

```yaml
- name: Run Django database migrations
  community.general.django_manage:
    command: migrate
    app_path: "{{ project_path }}"
    virtualenv: "{{ venv_path }}"
    settings: "{{ django_settings }}"
  environment: "{{ django_environment }}"
  register: migration_result
  failed_when:
    - migration_result.rc != 0
    - "'OperationalError' in migration_result.stderr"   # only fail on real errors
  changed_when: migration_result.stdout != ""             # migrations only report changed when applied
  tags: django.migrate
```

**Why it matters**: Migrations can fail due to schema conflicts or data issues. Separating them with a tag allows operators to run them intentionally (`--tags django.migrate`) after reviewing migration code. Using `register` + `failed_when` lets you distinguish "nothing to migrate" (ok) from actual migration failure.

**Authoritative sources**:
- [community.general.django_manage module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/django_manage_module.html)
- [YPCrumble/ansible-django-stack](https://github.com/YPCrumble/ansible-django-stack)

---

### 2.5 Static File Collection

**Practice**: Run `collectstatic` as a tagged task, run as the app user, notify a handler.

```yaml
- name: Collect Django static files
  community.general.django_manage:
    command: collectstatic
    app_path: "{{ project_path }}"
    virtualenv: "{{ venv_path }}"
    settings: "{{ django_settings }}"
  environment:
    DJANGO_SETTINGS_MODULE: "{{ django_settings }}"
  become: true
  become_user: "{{ app_user }}"
  notify: Reload nginx
  tags: django.static
```

**Why it matters**: `collectstatic` needs to write to `STATIC_ROOT` and may need the app user's permissions. Running it as the app user (not root) ensures correct file ownership. Notifying nginx reload ensures the web server picks up new static files.

---

### 2.6 File Permissions and Ownership

**Practice**: Always set `owner`, `group`, and `mode` explicitly on file and template tasks. Use `ansible.builtin.file` for directories.

```yaml
- name: Ensure app directory exists with correct permissions
  ansible.builtin.file:
    path: "{{ project_path }}"
    state: directory
    owner: "{{ app_user }}"
    group: "{{ app_group }}"
    mode: '0755'
    recurse: true

- name: Deploy .env file
  ansible.builtin.template:
    src: .env.j2
    dest: "{{ project_path }}/.env"
    owner: "{{ app_user }}"
    group: "{{ app_group }}"
    mode: '0640'
```

**Why it matters**: Without explicit ownership, files may be created as root and then unreadable by the gunicorn worker process. Quoting octal modes (e.g., `'0640'`) prevents YAML from parsing them as decimal.

**Authoritative sources**:
- [ansible.builtin.file module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/file_module.html)
- [CVE-2020-1736](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/file_module.html) — always specify mode explicitly

---

## 3. Ansible with Django Deployments

### 3.1 Managing SECRET_KEY and Django Settings

**Practice**: Render Django settings from a Jinja2 template; keep `SECRET_KEY` in Ansible Vault.

```yaml
# roles/django_app/templates/settings_production.py.j2
SECRET_KEY = "{{ django_secret_key }}"
DEBUG = {{ django_debug | to_json }}
ALLOWED_HOSTS = {{ django_allowed_hosts | to_json }}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '{{ db_name }}',
        'USER': '{{ db_user }}',
        'PASSWORD': '{{ db_password }}',
        'HOST': '{{ db_host }}',
        'PORT': '{{ db_port }}',
    }
}
```

**Why it matters**: Hardcoding secrets in settings files is a critical vulnerability. Using Ansible Vault + Jinja2 templating means secrets never touch version control, and the settings file is generated per-environment.

**Recommended implementation**:
- Store `django_secret_key` in `group_vars/<env>/vault` (encrypted).
- Render `settings_production.py` from a template as part of the deploy.
- Use `DJANGO_SETTINGS_MODULE` in the gunicorn systemd unit to point to the production settings.

---

### 3.2 Database Migrations

**Practice**: Tag migration tasks; run them explicitly; use `changed_when` to detect whether migrations were applied.

```yaml
- name: Check if migrations need to run
  community.general.django_manage:
    command: showmigrations
    app_path: "{{ project_path }}"
    virtualenv: "{{ venv_path }}"
    settings: "{{ django_settings }}"
  register: pending_migrations
  changed_when: "'[ ]' in pending_migrations.stdout"
```

**Why it matters**: `showmigrations` shows `[ ]` for unapplied migrations. Using it as a gate prevents unnecessary migration runs and gives you visibility into what will change.

**Recommended approach**: Run migrations as a separate step in your deploy playbook, tagged with `migrate`. Never run them implicitly as part of every configuration change.

---

### 3.3 Collectstatic

**Practice**: Run collectstatic only when static files have changed, as the app user.

```yaml
- name: Collect static files
  community.general.django_manage:
    command: collectstatic --noinput
    app_path: "{{ project_path }}"
    virtualenv: "{{ venv_path }}"
    settings: "{{ django_settings }}"
  become: true
  become_user: "{{ app_user }}"
  environment:
    DJANGO_SETTINGS_MODULE: "{{ django_settings }}"
  tags: deploy
```

**Why it matters**: Running as root can create files owned by root in `STATIC_ROOT`, breaking nginx's ability to serve them. The `--noinput` flag makes it non-interactive. Tagging with `deploy` lets you run it only during deploys.

---

### 3.4 Gunicorn systemd Service Configuration

**Practice**: Deploy a systemd unit file from a Jinja2 template; manage it with `systemd_service`; use Unix socket or TCP.

```yaml
# roles/gunicorn/templates/gunicorn.service.j2
[Unit]
Description={{ project_name }} gunicorn daemon
After=network.target postgresql.service

[Service]
Type=notify
User={{ app_user }}
Group={{ app_group }}
WorkingDirectory={{ project_path }}
Environment="DJANGO_SETTINGS_MODULE={{ django_settings }}"
ExecStart={{ venv_path }}/bin/gunicorn \\
  --workers {{ gunicorn_workers }} \\
  --bind unix:{{ venv_path }}/run/gunicorn.sock \\
  {{ wsgi_module }}
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```yaml
# tasks/main.yml
- name: Deploy gunicorn systemd unit
  ansible.builtin.template:
    src: gunicorn.service.j2
    dest: /etc/systemd/system/gunicorn.service
  notify: Restart gunicorn

- name: Ensure gunicorn socket directory exists
  ansible.builtin.file:
    path: "{{ venv_path }}/run"
    state: directory
    owner: "{{ app_user }}"
    group: "{{ app_group }}"
    mode: '0755'
```

**Why it matters**: Template-based unit files allow per-environment customization (workers, socket path, user). The `After=postgresql.service` ensures DB is ready before gunicorn starts. `Restart=on-failure` gives resilience.

**Real-world reference**: [YPCrumble/ansible-django-stack gunicorn_start.j2](https://github.com/YPCrumble/ansible-django-stack/blob/master/roles/web/templates/gunicorn_start.j2)

---

### 3.5 Environment File Management

**Practice**: Deploy `.env` from a template; keep it owned by the app user with restricted permissions.

```yaml
- name: Deploy environment file
  ansible.builtin.template:
    src: .env.j2
    dest: "{{ project_path }}/.env"
    owner: "{{ app_user }}"
    group: "{{ app_group }}"
    mode: '0640'
  notify: Restart gunicorn
```

```yaml
# .env.j2
DJANGO_SETTINGS_MODULE={{ django_settings }}
DATABASE_URL=postgres://{{ db_user }}:{{ db_password }}@{{ db_host }}:{{ db_port }}/{{ db_name }}
SECRET_KEY={{ django_secret_key }}
```

**Why it matters**: Environment files are the standard way to configure 12-factor Django apps. Deploying them via Ansible (not committing them) keeps secrets out of git. The systemd unit reads them via `EnvironmentFile=` or the gunicorn startup script sources them.

---

## 4. Ansible Testing and Validation

### 4.1 ansible-lint

**Practice**: Run `ansible-lint` in CI and pre-commit; enforce a baseline profile.

```bash
ansible-lint          # lint all playbooks/roles
ansible-lint --fix     # auto-fix what can be fixed
```

```yaml
# .ansible-lint
profile: production
warn_list:
  - experimental
  - fqcn[deep]    # allow deep FQCN checks for now
skip_list:
  - yaml[line-length]   # if needed
```

**Why it matters**: ansible-lint catches common errors (unnamed tasks, missing `state: present`, shell when `command` is sufficient, deprecated syntax). It enforces FQCN usage (`ansible.builtin.template` not `template`). In CI, it prevents broken playbooks from being merged.

**Authoritative sources**:
- [ansible-lint GitHub](https://github.com/ansible/ansible-lint)
- [ansible-lint configuration options (source)](https://github.com/ansible/ansible-lint/blob/main/src/ansiblelint/config.py)

---

### 4.2 ansible-playbook --check

**Practice**: Run playbooks in check mode for dry-run validation.

```bash
ansible-playbook -i inventories/production playbooks/webservers.yml --check --diff
```

**Why it matters**: `--check` shows what tasks would change without making changes. `--diff` shows the exact content differences for templated files. Combined with `--limit`, you can validate against a single host before running in production.

**Caveat**: Some modules (e.g., `django_manage`, `shell`) don't support check mode fully. Use `check_mode: false` only for tasks that truly can't be simulated.

---

### 4.3 Molecule

**Practice**: Use Molecule for role-level integration testing with Docker or Podman.

```yaml
# molecule/default/molecule.yml
driver:
  name: docker

platforms:
  - name: instance
    image: docker.io/python:3.13-slim
    pre_build_image: true

provisioner:
  name: ansible.builtin.ansible

verifier:
  name: ansible.builtin.assert
```

```yaml
# molecule/default/tasks/main.yml (test scenario)
- name: Verify nginx is installed
  ansible.builtin.assert:
    that:
      - "'/usr/sbin/nginx' is file"
```

**Why it matters**: Molecule spins up disposable containers, applies your role, and then runs verification tests. This catches idempotency failures (does the role report changed on second run?), missing dependencies, and broken templates before they reach production.

**Authoritative sources**:
- [Molecule GitHub](https://github.com/ansible/molecule)
- [Molecule docs](https://docs.ansible.com/projects/molecule/)

**Recommended implementation**:
- One `molecule/` directory per role (e.g., `roles/nginx/molecule/default/`).
- Use Docker driver for fast local testing; use Podman for rootless environments.
- Add `molecule test` to CI (GitHub Actions / GitLab CI).

---

### 4.4 CI Integration Patterns

**Practice**: Run lint + syntax check + Molecule in CI on every PR.

```yaml
# .github/workflows/ansible-ci.yml
name: Ansible CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ansible-lint
      - run: ansible-lint
  molecule:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install "molecule[docker]" ansible-core
      - run: molecule test
```

**Why it matters**: CI catches issues before they reach the deployment pipeline. ansible-lint + Molecule in CI ensures playbook quality and role correctness for every PR.

---

## 5. Ansible vs Alternatives

### 5.1 Ansible Pros and Cons

**Pros**:
- **Agentless**: No daemon on target hosts; uses SSH. Simplest possible architecture for a single-server deployment.
- **Declarative + procedural hybrid**: YAML playbooks are readable; tasks map directly to the operations you'd run manually.
- **Idempotent by convention**: Most modules are idempotent out of the box.
- **Large ecosystem**: 1000+ Galaxy roles for common services (nginx, postgresql, python, systemd).
- **Mature Django support**: `community.general.django_manage`, `community.general.pip` with virtualenv support.

**Cons**:
- **YAML limitations**: Conditionals, loops, and includes can become hard to read for complex logic.
- **No built-in rollback**: If a deploy breaks, you must manually reverse or redeploy.
- **Sequential by default**: Large inventories can be slow (mitigated by `strategy: free` or `async`).
- **Requires Python on managed nodes**: For modules that run Python (most builtins).

---

### 5.2 Alternatives

| Tool | Best for | When to use instead of Ansible |
|------|----------|-------------------------------|
| **SaltStack** | Event-driven, large-scale, real-time | Thousands of nodes; need push-based reaction to events |
| **Puppet** | Long-lived infrastructure, Ruby ecosystem | Large teams with Ruby expertise; strict modeling of desired state |
| **Chef** | Ruby DSL, cookbook ecosystem | Chef Supermarket cookbooks fit your stack |
| **Docker Compose** | Containerized apps | Your Django app is already in Docker; you want container isolation |
| **Kubernetes** | Orchestrated, multi-instance, cloud-native | Multiple replicas, auto-scaling, service mesh, rolling updates |
| **Terraform + Ansible** | Provisioning + configuration | When you need separate tooling for infra creation vs. configuration |

**For this specific project (Django app, single host, PostgreSQL + nginx + systemd)**:

**Ansible is the right choice** because:
- Agentless fits a single VPS or dedicated server perfectly.
- You're not running containers (Docker Compose/K8s add unnecessary complexity).
- The stack is standard Linux packages — Ansible's module library covers all of them.
- You need to run Django management commands (`migrate`, `collectstatic`) alongside system configuration — Ansible's procedural tasks are a natural fit.

**When something else is better**:
- If you containerize the app → Docker Compose (simpler) or Kubernetes (if you need scaling).
- If you have 100+ identical app servers → consider SaltStack or Puppet for their push models.

**Authoritative sources**:
- [Ansible vs Salt vs Puppet vs Chef — comparison](https://www.ansible.com/overview/alternatives)
- [Jeff Geerling, Ansible for DevOps](https://www.ansiblefordevops.com/)

---

## 6. Real-World Examples

### 6.1 Official Ansible Examples

**Source**: [docs.ansible.com Sample Setup](https://docs.ansible.com/projects/ansible/latest/tips_tricks/sample_setup.html)

The official sample shows a web service deployment with:
- `site.yml` importing `webservers.yml` and `dbservers.yml`
- Functional roles (`common`, `webtier`, `monitoring`)
- `group_vars/` and `host_vars/` at the project root
- Handlers for service restarts on config changes

**Relevance to this project**: Directly matches the Django deployment topology (web tier + database tier). The handler pattern for nginx reload on config change is directly applicable.

---

### 6.2 YPCrumble/ansible-django-stack

**Source**: [github.com/YPCrumble/ansible-django-stack](https://github.com/YPCrumble/ansible-django-stack) — 1.4k stars, 382 forks

**Architecture**:
- Roles: `base`, `web`, `db`, `nginx`, `rabbitmq`, `celery`, `certbot`
- Uses `community.general.django_manage` for `syncdb`, `migrate`, `collectstatic`
- Uses `community.general.pip` with `virtualenv` for Python packages
- Uses `ansible.builtin.template` for gunicorn startup script and nginx config
- Handlers for `Restart application` and `Restart nginx`
- `ansible-vault` for secrets
- Includes Molecule tests, `.ansible-lint` config

**Relevance**: This is the closest reference architecture to your project. It validates the role-based approach for each stack component.

---

### 6.3 Jeff Geerling — Ansible for DevOps

**Source**: [github.com/geerlingguy/ansible-for-devops](https://github.com/geerlingguy/ansible-for-devops) — 9.9k stars

**Key patterns**:
- Deployment playbooks for Passenger + Nginx (analogous to gunicorn + nginx)
- Rolling deployment patterns with `serial` keyword
- Molecule testing for roles
- LAMP stack examples with idempotent package and service management

**Relevance**: Jeff Geerling's patterns are widely adopted as community best practice. The deployment chapter covers zero-downtime deploy patterns using `serial`, `delegate_to`, and `flush_handlers`.

---

### 6.4 PostgreSQL + nginx + Django Reference Architecture

**Canonical pattern** (validated across multiple sources):

```
Inventory groups:
  [webservers]  →  nginx + gunicorn + django_app
  [dbservers]   →  postgresql (can be same host for single-server deploys)

Role execution order (webservers):
  1. common         — baseline packages, users, security
  2. python_venv    — create virtualenv, install Python
  3. postgresql_client — libpq, client config
  4. django_app     — clone code, install requirements, manage.py migrate, collectstatic
  5. gunicorn       — systemd unit, start service
  6. nginx          — site config, upstream to gunicorn socket
```

**Authoritative sources**:
- [Michal Karzynski — Django + nginx + gunicorn (blog)](http://michal.karzynski.pl/blog/2013/06/09/django-nginx-gunicorn-virtualenv-supervisor/) — the canonical reference (updated for systemd in later posts)
- [DigitalOcean — Django with Ansible and PostgreSQL](https://www.digitalocean.com/community/tutorials/how-to-deploy-django-applications-with-ansible-and-postgresql-on-ubuntu-20-04)

---

## Summary of Recommended Implementation

| Aspect | Recommendation |
|--------|---------------|
| **Layout** | `inventories/`, `playbooks/`, `roles/` with one role per stack component |
| **Variable storage** | `group_vars/all.yml` for defaults, `group_vars/vault` (encrypted) for secrets |
| **Secrets** | Ansible Vault with vars+vault pattern per environment |
| **systemd** | `ansible.builtin.systemd_service` with `state`, `enabled`, `daemon_reload` |
| **nginx** | Jinja2 template + `notify: Reload nginx` handler |
| **pip/venv** | `ansible.builtin.pip` with `virtualenv` and `requirements` params |
| **Migrations** | `community.general.django_manage command=migrate` — tagged, explicit |
| **Collectstatic** | `community.general.django_manage command=collectstatic` — tagged, run as app user |
| **SECRET_KEY** | Vaulted variable, injected via rendered `settings.py` template |
| **Gunicorn** | Template systemd unit, `After=postgresql.service`, `Restart=on-failure` |
| **Testing** | ansible-lint in CI + Molecule per role + `--check` for pre-deploy dry runs |
| **Tool choice** | Ansible is appropriate for single-host Django + PostgreSQL + nginx + systemd |
