# Create your views here.
from core.utils import TimeUtils
from .models import InsureeAnswer
#from django.http.response 
 
def register_answer(request):
     
    if request.method == "POST":
        new_ins_answer = InsureeAnswer(
        audit_user_id = request.POST.get('audit_user_id'),
        question = request.POST.get('question'),
        answer_score = request.POST.get('answer_score'),
        officer_id = request.POST.get('officer_id'),
        answer_date =  TimeUtils.now()
        )

        new_ins_answer.save()
        print(new_ins_answer)
    return new_ins_answer


def register_insuree_answer(request,data):
    data = request.POST.dict()
    for key in data:
        new_ins_answer = InsureeAnswer(
            audit_user_id = data['audit_user_id'],
            question = data['question'],
            answer_score = data['answer_score'],
            officer_id = data['officer_id'],
            answer_date =  TimeUtils.now()
        )
        return new_ins_answer

    return data       