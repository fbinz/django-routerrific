import json

from django import forms
from django.http import HttpResponse
from django.urls import path


def get_appointments(request) -> HttpResponse:
    return HttpResponse(
        json.dumps(
            {
                "appointments": [
                    {
                        "id": "appt_a52f12",
                        "owner": "user_b52f12",
                        "name": "Appointment 1",
                        "start": "2023-01-01T00:00:00",
                        "end": "2023-01-01T01:00:00",
                        "address": {
                            "id": "addr_e12f12",
                            "street": "Main Street",
                            "number": "123",
                            "city": "Berlin",
                            "zip": "10115",
                        },
                    },
                    {
                        "id": "appt_cd2f12",
                        "name": "Appointment 2",
                        "owner": "user_b52f12",
                        "start": "2023-01-01T01:00:00",
                        "end": "2023-01-01T02:00:00",
                        "address": {
                            "id": "addr_2d2f12",
                            "street": "Rhein Street",
                            "number": "456",
                            "city": "Cologne",
                            "zip": "54321",
                        },
                    },
                ]
            }
        ),
        status=200,
        content_type="application/json",
    )


class AppointmentUpdateForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    start = forms.DateTimeField(required=False)
    end = forms.DateTimeField(required=False)


def update_appointment(request, appointment_id: str) -> HttpResponse:
    form = AppointmentUpdateForm(request.POST)
    if not form.is_valid():
        return HttpResponse("Bad Request", status=400)

    # check that the user is the owner of the appointment
    appointment = Appointment.objects.get(id=appointment_id)
    user = request.user
    if user != appointment.owner:
        return HttpResponse("Forbidden", status=403)

    if name := form.cleaned_data.get("name"):
        appointment.name = name

    if start := form.cleaned_data.get("start"):
        appointment.start = start

    if end := form.cleaned_data.get("end"):
        appointment.end = end

    appointment.save()

    return HttpResponse(
        json.dumps(
            {
                "appointment": {
                    "id": appointment.id,
                    "name": appointment.name,
                    "start": appointment.start,
                    "end": appointment.end,
                    "address": {
                        "id": appointment.address.id,
                        "street": appointment.address.street,
                        "number": appointment.address.number,
                        "city": appointment.address.city,
                        "zip": appointment.address.zip,
                    },
                }
            }
        ),
        status=200,
        content_type="application/json",
    )


urlpatterns = [
    path(
        "appointments",
        view(
            get=[get_appointments],
            post=[create_appointment],
        ),
    ),
    path(
        "appointments/<str:appointment_id>",
        view(
            get=[get_appointment],
            put=[update_appointment],
            delete=[delete_appointment, delete_appointment_legacy],
        ),
    ),
]
