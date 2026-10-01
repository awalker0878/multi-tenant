"""Profile catalog loading.

Catalogs are reviewed JSON under `profiles/<family>/catalog.json`. The directory
is the only index: there is no second profile list to drift out of date.

A catalog is also the machine-readable owner of the portable policy defaults: the
default profile of a family, the portable service list and its default profiles,
and the request-shape defaults a caller may omit. Nothing a reviewer must be able
to change lives only in code.

Every catalog and every profile entry carries an explicit reviewed version, and the
whole reviewed catalog set has a canonical digest. Both are recorded on every
resolution, so a plan states the exact reviewed revision it was built against.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.capabilities import CAPABILITIES
from provisioner.domain.capability_properties import parse_requirements
from provisioner.domain.request import digest
from provisioner.profiles.requirements import validate_requirements
from hosting_resources import RESOURCE_ROOT as ROOT

PROFILE_ROOT = ROOT / 'profiles'

FAMILIES = ('environment', 'security', 'assurance', 'availability', 'recovery',
            'compute', 'storage', 'network', 'service', 'placement')

DEFERRED = 'DEFERRED_NOT_IMPLEMENTED'
STATUSES = ('IMPLEMENTED_INTERNAL_IPV4_OZ_RZ', DEFERRED)

#: A reviewed version is a positive integer revision written as a JSON string.
VERSION = re.compile(r'^[1-9][0-9]*$')

#: Families whose catalog must declare which of their profiles is the default.
DEFAULT_OWNERS = ('assurance', 'compute', 'network', 'recovery', 'storage')

CATALOG_KEYS = {'family', 'version', 'description', 'default', 'services', 'defaults',
                'requestDefaults', 'profiles'}
ENTRY_KEYS = {'profile', 'version', 'rank', 'status', 'description', 'requires',
              'platform_inputs', 'limits'}


def _relative(path: Path) -> str:
    """A path a reader can locate, whether or not it is inside this repository."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _version(value, owner: str, path: str) -> str:
    if value is None:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'{owner} declares no reviewed version', path=path)
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'{owner} version {value!r} is not a positive integer revision',
                                path=path)
    return value


@dataclass(frozen=True)
class Profile:
    family: str
    profile: str
    version: str
    rank: int
    status: str
    description: str
    requires: dict = field(default_factory=dict)
    platform_inputs: dict = field(default_factory=dict)
    limits: tuple[str, ...] = ()

    @property
    def implemented(self) -> bool:
        return self.status == 'IMPLEMENTED_INTERNAL_IPV4_OZ_RZ'

    @property
    def trust(self) -> str | None:
        return self.requires.get('trust')

    @property
    def service_class(self) -> str | None:
        return self.requires.get('service_class')

    def to_dict(self) -> dict:
        return {'family': self.family, 'profile': self.profile, 'version': self.version,
                'rank': self.rank, 'status': self.status, 'description': self.description,
                'requires': dict(self.requires),
                'platform_inputs': dict(self.platform_inputs),
                'limits': list(self.limits)}


@dataclass(frozen=True)
class Catalog:
    families: dict[str, dict[str, Profile]]
    versions: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    request_defaults: dict[str, dict] = field(default_factory=dict)
    services: tuple[str, ...] = ()
    service_defaults: dict[str, str] = field(default_factory=dict)
    digest: str = ''

    def get(self, family: str, profile: str) -> Profile:
        if family not in self.families:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile family: {family}',
                                    path=f'$.spec.{family}',
                                    details={'families': sorted(self.families)})
        if profile not in self.families[family]:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Unknown {family} profile: {profile}',
                                    path=f'$.spec.{family}',
                                    details={'available': sorted(self.families[family])})
        return self.families[family][profile]

    def family(self, family: str) -> dict[str, Profile]:
        return self.families.get(family, {})

    def by_rank(self, family: str) -> list[Profile]:
        return sorted(self.family(family).values(), key=lambda p: (p.rank, p.profile))

    def names(self) -> dict[str, list[str]]:
        return {f: sorted(p) for f, p in sorted(self.families.items())}

    def version(self, family: str) -> str:
        """The reviewed revision of one catalog."""
        if family not in self.versions:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'No reviewed catalog version for family {family}',
                                    path=f'$.spec.{family}',
                                    details={'families': sorted(self.versions)})
        return self.versions[family]

    def default(self, family: str) -> str:
        """The profile this family's catalog declares when a request omits one."""
        if family not in self.defaults:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Profile family {family} declares no default profile',
                                    path=f'$.spec.{family}',
                                    details={'families': sorted(self.defaults)})
        return self.defaults[family]

    def request_default(self, family: str) -> dict:
        """Request-shape defaults the family's catalog declares for absent fields."""
        return {key: value for key, value in self.request_defaults.get(family, {}).items()}

    def service_names(self) -> tuple[str, ...]:
        """The portable service list, owned by the service catalog."""
        return self.services

    def service_default(self, service: str) -> str:
        if service not in self.service_defaults:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Portable service {service} declares no default profile',
                                    path='$.spec.services',
                                    details={'services': list(self.services)})
        return self.service_defaults[service]

    def manifest(self) -> dict:
        """The full reviewed catalog content, in canonical order."""
        return {
            'families': {
                family: {'version': self.versions[family],
                         'default': self.defaults.get(family),
                         'requestDefaults': dict(self.request_defaults.get(family, {})),
                         'profiles': {name: profile.to_dict()
                                      for name, profile in sorted(profiles.items())}}
                for family, profiles in sorted(self.families.items())},
            'services': list(self.services),
            'serviceDefaults': dict(self.service_defaults),
        }

    def version_set(self) -> dict:
        """Every catalog revision and every profile revision, as one reviewable set."""
        return {
            'catalogs': {family: self.versions[family] for family in sorted(self.versions)},
            'profiles': {family: {name: profile.version
                                  for name, profile in sorted(profiles.items())}
                         for family, profiles in sorted(self.families.items())},
        }


def _load_one(path: Path) -> tuple[str, dict]:
    family = path.parent.name
    relative = _relative(path)
    if family not in FAMILIES:
        raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile family: {family}', path=relative)
    try:
        with path.open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Profile catalog exceeds bounded size')
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('Duplicate profile property')
                result[key] = value
            return result
        def reject(_):
            raise ValueError('Non-finite profile value')
        document = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    except (OSError, ValueError) as exc:
        raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unreadable profile catalog: {exc}',
                                path=relative) from exc
    if not isinstance(document, dict):
        raise ProvisioningError('UNSUPPORTED_PROFILE', 'Profile catalog must be a mapping',
                                path=relative)
    if document.get('family') != family:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'Catalog family {document.get("family")!r} does not match directory {family!r}',
                                path=relative)
    unknown = sorted(set(document) - CATALOG_KEYS)
    if unknown:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'Unknown profile catalog field: {unknown}', path=relative)
    version = _version(document.get('version'), 'Profile catalog', relative)

    rows = document.get('profiles')
    if not isinstance(rows, list) or not rows:
        raise ProvisioningError('UNSUPPORTED_PROFILE', 'Empty profile catalog', path=relative)
    profiles: dict[str, Profile] = {}
    ranks: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict) or not {'profile', 'rank', 'status', 'description'} <= set(row):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Incomplete profile entry',
                                    path=relative)
        unknown = sorted(set(row) - ENTRY_KEYS)
        if unknown:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Unknown profile entry field in {row.get("profile")}: {unknown}',
                                    path=relative)
        if row['status'] not in STATUSES:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile status: {row["status"]}',
                                    path=relative)
        if (not isinstance(row['profile'], str) or not row['profile'].strip()
                or len(row['profile']) > 128 or type(row['rank']) is not int
                or row['rank'] <= 0 or not isinstance(row['description'], str)
                or not row['description'].strip()):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Invalid profile identity or rank',
                                    path=relative)
        requirements = row.get('requires', {})
        inputs = row.get('platform_inputs', {})
        limits = row.get('limits', [])
        if not isinstance(requirements, dict) or not isinstance(inputs, dict):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Profile requirements and inputs must be mappings',
                                    path=relative)
        validate_requirements(family, requirements, path=relative)
        capabilities = requirements.get('capabilities', [])
        if (not isinstance(capabilities, list)
                or any(not isinstance(cap, str) for cap in capabilities)
                or len(capabilities) != len(set(capabilities))
                or not set(capabilities) <= CAPABILITIES):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Profile capabilities must be unique reviewed IDs',
                                    path=relative)
        if (not isinstance(limits, list)
                or any(not isinstance(limit, str) or not limit.strip() for limit in limits)):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Profile limits must be nonempty text entries',
                                    path=relative)
        try:
            parse_requirements(requirements.get('constraints', []), capabilities)
        except ValueError as exc:
            raise ProvisioningError('UNSUPPORTED_PROFILE', str(exc), path=relative) from exc
        entry_version = _version(row.get('version'), f'Profile {row.get("profile")}', relative)
        rank_key = (row['profile'].split('/', 1)[0] if '/' in row['profile'] else family, row['rank'])
        if row['profile'] in profiles or rank_key in ranks:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Duplicate profile or rank: {row["profile"]}',
                                    path=relative)
        profiles[row['profile']] = Profile(
            family=family, profile=row['profile'], version=entry_version, rank=row['rank'],
            status=row['status'], description=row['description'],
            requires=dict(row.get('requires', {})),
            platform_inputs=dict(row.get('platform_inputs', {})),
            limits=tuple(row.get('limits', [])))
        ranks.add(rank_key)

    default = document.get('default')
    if default is not None:
        if not isinstance(default, str) or default not in profiles:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Catalog default {default!r} is not a profile of {family}',
                                    path=relative)
        if not profiles[default].implemented:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Catalog default {default} is deferred and cannot be a default',
                                    path=relative)

    services = document.get('services')
    service_defaults = document.get('defaults')
    if family != 'service' and (services is not None or service_defaults is not None):
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                'Only the service catalog declares the portable service list',
                                path=relative)
    if services is not None:
        if (not isinstance(services, list) or not services
                or not all(isinstance(name, str) and name for name in services)
                or len(set(services)) != len(services)):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Invalid portable service list',
                                    path=relative)
        for name in services:
            if not any(profile.startswith(f'{name}/') for profile in profiles):
                raise ProvisioningError('UNSUPPORTED_PROFILE',
                                        f'Portable service {name} has no profile in the service catalog',
                                        path=relative)
    if service_defaults is not None:
        if not isinstance(service_defaults, dict):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Invalid portable service defaults',
                                    path=relative)
        if sorted(service_defaults) != sorted(services or []):
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    'Portable service defaults must name every service exactly once',
                                    path=relative)
        for name, profile in service_defaults.items():
            if not isinstance(profile, str) or f'{name}/{profile}' not in profiles:
                raise ProvisioningError('UNSUPPORTED_PROFILE',
                                        f'Default profile {name}/{profile} is not in the service catalog',
                                        path=relative)
            if not profiles[f'{name}/{profile}'].implemented:
                raise ProvisioningError('UNSUPPORTED_PROFILE',
                                        f'Default profile {name}/{profile} is deferred',
                                        path=relative)

    request_defaults = document.get('requestDefaults', {})
    if not isinstance(request_defaults, dict) or not all(
            isinstance(group, dict) for group in request_defaults.values()):
        raise ProvisioningError('UNSUPPORTED_PROFILE', 'Invalid request defaults', path=relative)

    return family, {'version': version, 'profiles': profiles, 'default': default,
                    'services': tuple(services or ()),
                    'defaults': dict(service_defaults or {}),
                    'requestDefaults': {key: dict(value)
                                        for key, value in request_defaults.items()}}


def load_catalogs(root: Path = PROFILE_ROOT) -> Catalog:
    families: dict[str, dict[str, Profile]] = {}
    versions: dict[str, str] = {}
    defaults: dict[str, str] = {}
    request_defaults: dict[str, dict] = {}
    services: tuple[str, ...] = ()
    service_defaults: dict[str, str] = {}
    for path in sorted(root.glob('*/catalog.json')):
        family, loaded = _load_one(path)
        families[family] = loaded['profiles']
        versions[family] = loaded['version']
        if loaded['default'] is not None:
            defaults[family] = loaded['default']
        if loaded['requestDefaults']:
            request_defaults[family] = loaded['requestDefaults']
        if family == 'service':
            services = loaded['services']
            service_defaults = loaded['defaults']

    missing = [family for family in FAMILIES if family not in families]
    if missing:
        raise ProvisioningError('UNSUPPORTED_PROFILE', f'Missing profile catalogs: {missing}')
    undeclared = [family for family in DEFAULT_OWNERS if family not in defaults]
    if undeclared:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'Profile catalogs declare no default profile: {undeclared}')
    if not services or not service_defaults:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                'The service catalog must declare the portable service list '
                                'and its default profiles')
    repeated = sorted({version for version in versions.values()
                       if list(versions.values()).count(version) > 1})
    if repeated:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'Catalog versions must form one reviewed revision ladder: {repeated}',
                                details={'versions': dict(versions)})

    catalog = Catalog(families=families, versions=versions, defaults=defaults,
                      request_defaults=request_defaults, services=services,
                      service_defaults=service_defaults)
    return replace(catalog, digest=digest(catalog.manifest()))
