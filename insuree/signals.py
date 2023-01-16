from core.signals import Signal
from django.db.models.signals import post_save
from .models import InsureeAnswer, Insuree
from django.dispatch import receiver



_insuree_policy_before_query_signal_params = ["user", "additional_filter"]
signal_before_insuree_policy_query = Signal(providing_args=_insuree_policy_before_query_signal_params)
signal_before_family_query = Signal(providing_args=_insuree_policy_before_query_signal_params)


def _read_signal_results(result_signal):
    # signal result is a representation of list of tuple (function, result)
    return [result[1] for result in result_signal if result[1] is not None]


@receiver(post_save, sender=Insuree)
def create_insuree_response(sender, instance, created, **kwargs):
    if created:
        attrs = ['answer_date','question','answer_score','officer_id','audit_user_id','',]
        saves=InsureeAnswer.objects.create(
            insuree_id=instance,
            answer_date = instance.answer_date,
            question = instance.question,
            answer_score = instance.answer_score,
            officer_id = instance.officer_id,
            audit_user_id = instance.audit_user_id
            )
        saves.save()

@receiver(post_save, sender=InsureeAnswer)
def insuree_score_service(sender, instance,created, **kwargs):
        id = instance.insuree_id.id
        if created:
            answer_collection = InsureeAnswer.objects.filter(insuree_id = instance.insuree_id)
            score = sum([item.answer_score.option_value for item in answer_collection])
            score +=score
            insuree_to_update = Insuree.objects.get(id = id)
            insuree_to_update.total_score = score
            insuree_to_update.save()        

        return score