import logging
from pickle import TRUE
import uuid
import pathlib
import base64
import graphene

from insuree.services import validate_insuree_number, InsureeService, FamilyService, validate_temporary_insuree_number, TemporaryInsureeService

from .apps import InsureeConfig
from core.schema import OpenIMISMutation
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext as _
from graphene import InputObjectType
from .models import Family, Insuree, FamilyMutation, InsureeMutation, TemporaryInsuree, TemporaryInsureeMutation
from policy.models import Policy
from location import models as location_models

logger = logging.getLogger(__name__)


class PhotoInputType(InputObjectType):
    id = graphene.Int(required=False, read_only=True)
    uuid = graphene.String(required=False)
    date = graphene.Date(required=False)
    officer_id = graphene.Int(required=False)
    photo = graphene.String(required=False)
    filename = graphene.String(required=False)
    folder = graphene.String(required=False)


class InsureeBase:
    id = graphene.Int(required=False, read_only=True)
    uuid = graphene.String(required=False)
    chf_id = graphene.String(max_length=12, required=False)
    last_name = graphene.String(max_length=100, required=True)
    other_names = graphene.String(max_length=100, required=True)
    gender_id = graphene.String(max_length=1, required=True, description="Was mandatory in Legacy but not in modular")
    dob = graphene.Date(required=True)
    
    dod = graphene.Date(required=False)
    dead = graphene.Boolean(required=False)
    deathReason = graphene.String(max_length=500, required=False)

    head = graphene.Boolean(required=False)
    marital = graphene.String(max_length=1, required=False)
    passport = graphene.String(max_length=25, required=False)
    phone = graphene.String(max_length=50, required=False)
    email = graphene.String(max_length=100, required=False)
    current_address = graphene.String(max_length=200, required=False)
    geolocation = graphene.String(max_length=250, required=False)
    current_village_id = graphene.Int(required=False)
    photo_id = graphene.Int(required=False)
    photo_date = graphene.Date(required=False)
    photo = graphene.Field(PhotoInputType, required=False)
    card_issued = graphene.Boolean(required=False)
    family_id = graphene.Int(required=False)
    relationship_id = graphene.Int(required=False)
    profession_id = graphene.Int(required=False)
    education_id = graphene.Int(required=False)
    type_of_id_id = graphene.String(max_length=1, required=False)
    health_facility_id = graphene.Int(required=False)
    offline = graphene.Boolean(required=False)
    json_ext = graphene.types.json.JSONString(required=False)

class TemporaryInsureeBase:
    id = graphene.Int(required=False, read_only=True)
    uuid = graphene.String(required=False)
    chf_id = graphene.String(max_length=12, required=False)
    temporaryMPI = graphene.String(max_length=36, required=False)
    json_ext = graphene.types.json.JSONString(required=False)

class CreateInsureeInputType(InsureeBase, OpenIMISMutation.Input):
    pass

class CreateTemporaryInsureeInputType(TemporaryInsureeBase, OpenIMISMutation.Input):
    pass

class UpdateInsureeInputType(InsureeBase, OpenIMISMutation.Input):
    pass


class FamilyHeadInsureeInputType(InsureeBase, InputObjectType):
    pass


class FamilyBase:
    id = graphene.Int(required=False, read_only=True)
    uuid = graphene.String(required=False)
    location_id = graphene.Int(required=False)
    poverty = graphene.Boolean(required=False)
    family_type_id = graphene.String(max_length=1, required=False)
    address = graphene.String(max_length=200, required=False)
    is_offline = graphene.Boolean(required=False)
    ethnicity = graphene.String(max_length=1, required=False)
    confirmation_no = graphene.String(max_length=12, required=False)
    confirmation_type_id = graphene.String(max_length=3, required=False)
    json_ext = graphene.types.json.JSONString(required=False)

    contribution = graphene.types.json.JSONString(required=False)

    head_insuree = graphene.Field(FamilyHeadInsureeInputType, required=False)


class FamilyInputType(FamilyBase, OpenIMISMutation.Input):
    pass


class CreateFamilyInputType(FamilyInputType):
    pass


class UpdateFamilyInputType(FamilyInputType):
    pass


def create_file(date, insuree_id, photo_bin):
    date_iso = date.isoformat()
    root = InsureeConfig.insuree_photos_root_path
    file_dir = '%s/%s/%s/%s' % (
        date_iso[0:4],
        date_iso[5:7],
        date_iso[8:10],
        insuree_id
    )
    file_name = uuid.uuid4()
    file_path = '%s/%s' % (file_dir, file_name)
    pathlib.Path('%s/%s' % (root, file_dir)).mkdir(parents=True, exist_ok=True)
    f = open('%s/%s' % (root, file_path), "xb")
    f.write(base64.b64decode(photo_bin))
    f.close()
    return file_dir, file_name


def update_or_create_insuree(data, user):
    data.pop('client_mutation_id', None)
    data.pop('client_mutation_label', None)
    return InsureeService(user).create_or_update(data)

def update_or_create_temporary_insuree(data, user):
    data.pop('client_mutation_id', None)
    data.pop('client_mutation_label', None)
    return TemporaryInsureeService(user).create_or_update(data)

def update_or_create_family(data, user):
    data.pop('client_mutation_id', None)
    data.pop('client_mutation_label', None)
    return FamilyService(user).create_or_update(data)


class CreateFamilyMutation(OpenIMISMutation):
    """
    Create a new family, with its head insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "CreateFamilyMutation"

    class Input(CreateFamilyInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_families_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            from core.utils import TimeUtils
            data['validity_from'] = TimeUtils.now()
            client_mutation_id = data.get("client_mutation_id")
            # Validate insuree number right away
            errors = validate_insuree_number(data.get("head_insuree", {}).get("chf_id", None), True)
            if errors:
                return errors
            family = update_or_create_family(data, user)
            FamilyMutation.object_mutated(user, client_mutation_id=client_mutation_id, family=family)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_create_family")
            return [{
                'message': _("insuree.mutation.failed_to_create_family"),
                'detail': str(exc)}
            ]


class UpdateFamilyMutation(OpenIMISMutation):
    """
    Update an existing family, with its head insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "UpdateFamilyMutation"

    class Input(UpdateFamilyInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_update_families_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            client_mutation_id = data.get("client_mutation_id")
            family = update_or_create_family(data, user)
            FamilyMutation.object_mutated(user, client_mutation_id=client_mutation_id, family=family)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_update_family")
            return [{
                'message': _("insuree.mutation.failed_to_update_family"),
                'detail': str(exc)}
            ]


class DeleteFamiliesMutation(OpenIMISMutation):
    """
    Delete one or several families (and all its insurees).
    """
    _mutation_module = "insuree"
    _mutation_class = "DeleteFamiliesMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)
        delete_members = graphene.Boolean(required=False, default_value=False)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_delete_families_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for family_uuid in data["uuids"]:
            family = Family.objects \
                .prefetch_related('members') \
                .filter(uuid=family_uuid) \
                .first()
            if family is None:
                errors.append({
                    'title': family_uuid,
                    'list': [{'message': _("insuree.mutation.failed_to_delete_family") % {'uuid': family_uuid}}]
                })
                continue
            errors += FamilyService(user).set_deleted(family, data["delete_members"])
        if len(errors) == 1:
            errors = errors[0]['list']
        return errors


class CreateInsureeMutation(OpenIMISMutation):
    """
    Create a new insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "CreateInsureeMutation"

    class Input(CreateInsureeInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_insurees_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            from core.utils import TimeUtils
            data['validity_from'] = TimeUtils.now()
            client_mutation_id = data.get("client_mutation_id")
            # Validate insuree number right away
            errors = validate_insuree_number(data.get("chf_id", None), True)
            if errors:
                return errors
            insuree = update_or_create_insuree(data, user)
            InsureeMutation.object_mutated(user, client_mutation_id=client_mutation_id, insuree=insuree)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_create_insuree")
            return [{
                'message': _("insuree.mutation.failed_to_create_insuree"),
                'detail': str(exc)}
            ]


class UpdateInsureeMutation(OpenIMISMutation):
    """
    Update an existing insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "UpdateInsureeMutation"

    class Input(CreateInsureeInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_insurees_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            client_mutation_id = data.get("client_mutation_id")
            insuree = update_or_create_insuree(data, user)
            ## If an insuree is considered Dead, we suspend all family policy linked to this insuree
            if insuree.dead == True : 
                listPolicy = Policy.objects.filter(family=insuree.family).all()
                for policy in listPolicy :
                    policy.status=4
                    policy.save()

            InsureeMutation.object_mutated(user, client_mutation_id=client_mutation_id, insuree=insuree)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_update_insuree")
            return [{
                'message': _("insuree.mutation.failed_to_update_insuree"),
                'detail': str(exc)}
            ]


class DeleteInsureesMutation(OpenIMISMutation):
    """
    Delete one or several insurees.
    """
    _mutation_module = "insuree"
    _mutation_class = "DeleteInsureesMutation"

    class Input(OpenIMISMutation.Input):
        uuid = graphene.String(required=False)  # family uuid, to 'lock' family while mutation is processed
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_delete_insurees_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for insuree_uuid in data["uuids"]:
            insuree = Insuree.objects \
                .prefetch_related('family') \
                .filter(uuid=insuree_uuid) \
                .first()
            if insuree is None:
                errors.append({
                    'title': insuree_uuid,
                    'list': [{'message': _(
                        "insuree.validation.id_does_not_exist") % {'id': insuree_uuid}}]
                })
                continue
            if insuree.family and insuree.family.head_insuree.id == insuree.id:
                errors.append({
                    'title': insuree_uuid,
                    'list': [{'message': _(
                        "insuree.validation.delete_head_insuree") % {'id': insuree_uuid}}]
                })
                continue
            errors += InsureeService(user).set_deleted(insuree)
        if len(errors) == 1:
            errors = errors[0]['list']
        return errors


class RemoveInsureesMutation(OpenIMISMutation):
    """
    Delete one or several insurees.
    """
    _mutation_module = "insuree"
    _mutation_class = "RemoveInsureesMutation"

    class Input(OpenIMISMutation.Input):
        uuid = graphene.String()
        uuids = graphene.List(graphene.String)
        cancel_policies = graphene.Boolean(default_value=False)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_delete_insurees_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for insuree_uuid in data["uuids"]:
            insuree = Insuree.objects \
                .prefetch_related('family') \
                .filter(uuid=insuree_uuid) \
                .first()
            if insuree is None:
                errors += {
                    'title': insuree_uuid,
                    'list': [{'message': _(
                        "insuree.validation.id_does_not_exist") % {'id': insuree_uuid}}]
                }
                continue
            if insuree.family.head_insuree.id == insuree.id:
                errors.append({
                    'title': insuree_uuid,
                    'list': [{'message': _(
                        "insuree.validation.remove_head_insuree") % {'id': insuree_uuid}}]
                })
                continue
            insuree_service = InsureeService(user)
            if data['cancel_policies']:
                errors += insuree_service.cancel_policies(insuree)
            errors += insuree_service.remove(insuree)
        if len(errors) == 1:
            errors = errors[0]['list']
        return errors


class SetFamilyHeadMutation(OpenIMISMutation):
    """
    Set (change) the family head insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "SetFamilyHeadMutation"

    class Input(OpenIMISMutation.Input):
        uuid = graphene.String()
        insuree_uuid = graphene.String()

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_update_families_perms):
            raise PermissionDenied(_("unauthorized"))
        try:
            family = Family.objects.get(uuid=data['uuid'])
            insuree = Insuree.objects.get(uuid=data['insuree_uuid'])
            family.save_history()
            prev_head = family.head_insuree
            if prev_head:
                prev_head.save_history()
                prev_head.head = False
                prev_head.save()
            family.head_insuree = insuree
            family.save()
            insuree.save_history()
            insuree.head = True
            insuree.save()
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_set_head_insuree")
            return [{
                'message': _("insuree.mutation.failed_to_set_head_insuree"),
                'detail': str(exc)}
            ]


class ChangeInsureeFamilyMutation(OpenIMISMutation):
    """
    Set (change) the family of an insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "ChangeInsureeFamilyMutation"

    class Input(OpenIMISMutation.Input):
        family_uuid = graphene.String()
        insuree_uuid = graphene.String()
        cancel_policies = graphene.Boolean(default_value=False)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_update_families_perms) or \
                not user.has_perms(InsureeConfig.gql_mutation_update_insurees_perms):
            raise PermissionDenied(_("unauthorized"))
        try:
            family = Family.objects.get(uuid=data['family_uuid'])
            insuree = Insuree.objects.get(uuid=data['insuree_uuid'])
            insuree.save_history()
            insuree.family = family
            insuree.save()
            if data['cancel_policies']:
                return InsureeService(user).cancel_policies(insuree)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_change_insuree_family")
            return [{
                'message': _("insuree.mutation.failed_to_change_insuree_family"),
                'detail': str(exc)}
            ]

def create_family_for_insurees_without_family(user, data):
    insurees_without_family = Insuree.objects.filter(family__isnull=True, validity_to__isnull = True)
    data['audit_user_id'] = user.id_for_audit
    from core.utils import TimeUtils
    for insuree in insurees_without_family:
        data['validity_from'] = TimeUtils.now()
        client_mutation_id = data.get("client_mutation_id")

        head_insuree_data = {
            'id': insuree.id,
            'uuid': insuree.uuid,
            'chf_id': insuree.chf_id,
            'last_name': insuree.last_name,
            'other_names': insuree.other_names,
            'gender_id': insuree.gender_id,
            'dob': insuree.dob,
            'head': insuree.head,
            'marital': insuree.marital,
            'passport': insuree.passport,
            'phone': insuree.phone,
            'email': insuree.email,
            'current_address': insuree.current_address,
            'geolocation': insuree.geolocation,
            'current_village_id': insuree.current_village_id,
            'photo_id': insuree.photo_id,
            'photo_date': insuree.photo_date,
            'card_issued': insuree.card_issued,
            'relationship_id': insuree.relationship_id,
            'profession_id': insuree.profession_id,
            'education_id': insuree.education_id,
            'type_of_id_id': insuree.type_of_id_id,
            'health_facility_id': insuree.health_facility_id,
            'offline': insuree.offline,
            'audit_user_id': insuree.audit_user_id
        }

        data['head_insuree'] = head_insuree_data

        if (head_insuree_data["current_village_id"]):
            current_village_id = head_insuree_data["current_village_id"]
            current_village = location_models.Location.objects.get(id=current_village_id)
            data["location"] = current_village
        else:
            data["location"] = location_models.Location.objects.get(id=1)

        family = update_or_create_family(data, user)
        FamilyMutation.object_mutated(
            user, client_mutation_id=client_mutation_id, family=family)

        insuree.family = family
        insuree.save()
        InsureeMutation.object_mutated(
                user, client_mutation_id=client_mutation_id, insuree=insuree)

        logger.exception(f"Famille créée pour l'assuré {insuree.chf_id}")

    return None  

class CreateInsureesFamiliesMutation(OpenIMISMutation):
    """
    Create families for all valid insured persons who do not yet have one
    """
    _mutation_module = "insuree"
    _mutation_class = "CreateInsureesFamiliesMutation"

    class Input(CreateFamilyInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_families_perms):
                raise PermissionDenied(_("unauthorized"))
            create_family_for_insurees_without_family(user, data)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_create_families")
            return [{
                'message': _("insuree.mutation.failed_to_create_families"),
                'detail': str(exc)}
            ]
              
class CreateTemporaryInsureeMutation(OpenIMISMutation):
    """
    Create a new temporary insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "CreateTemporaryInsureeMutation"

    class Input(CreateTemporaryInsureeInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_insurees_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            from core.utils import TimeUtils
            data['validity_from'] = TimeUtils.now()
            client_mutation_id = data.get("client_mutation_id")
            # Validate insuree number right away
            errors = validate_temporary_insuree_number(data.get("chf_id", None), True)
            if errors:
                return errors
            insuree = update_or_create_temporary_insuree(data, user)
            TemporaryInsureeMutation.object_mutated(user, client_mutation_id=client_mutation_id, temporaryInsuree=insuree)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_create_insuree")
            return [{
                'message': _("insuree.mutation.failed_to_create_insuree"),
                'detail': str(exc)}
            ]


class UpdateTemporaryInsureeMutation(OpenIMISMutation):
    """
    Update an existing temporary insuree
    """
    _mutation_module = "insuree"
    _mutation_class = "UpdateTemporaryInsureeMutation"

    class Input(CreateTemporaryInsureeInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(InsureeConfig.gql_mutation_create_insurees_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            client_mutation_id = data.get("client_mutation_id")
            insuree = update_or_create_temporary_insuree(data, user)

            TemporaryInsureeMutation.object_mutated(user, client_mutation_id=client_mutation_id, temporaryInsuree=insuree)
            return None
        except Exception as exc:
            logger.exception("insuree.mutation.failed_to_update_temporary_insuree")
            return [{
                'message': _("insuree.mutation.failed_to_update_temporary_insuree"),
                'detail': str(exc)}
            ]


class DeleteTemporaryInsureesMutation(OpenIMISMutation):
    """
    Delete one or several temporary insurees.
    """
    _mutation_module = "insuree"
    _mutation_class = "DeleteTemporaryInsureesMutation"

    class Input(OpenIMISMutation.Input):
        uuid = graphene.String(required=False)  # family uuid, to 'lock' family while mutation is processed
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(InsureeConfig.gql_mutation_delete_insurees_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for insuree_uuid in data["uuids"]:
            insuree = TemporaryInsuree.objects \
                .filter(uuid=insuree_uuid) \
                .first()
            if insuree is None:
                errors.append({
                    'title': insuree_uuid,
                    'list': [{'message': _(
                        "insuree.validation.id_does_not_exist") % {'id': insuree_uuid}}]
                })
                continue
            errors += TemporaryInsureeService(user).set_deleted(insuree)
        if len(errors) == 1:
            errors = errors[0]['list']
        return errors