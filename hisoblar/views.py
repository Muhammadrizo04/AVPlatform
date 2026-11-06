from django.contrib.auth import views as auth_views

from .huquqlar import huquqi_bor

KIRISH_YOQ = "Panelga kirish huquqi yo'q"


class KirishView(auth_views.LoginView):
    template_name = "hisoblar/kirish.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Parol to'g'ri bo'lsa ham, rol panelga ham, reviziya o'tkazishga ham ruxsat bermasa sessiya ochilmaydi.
        # Revizor (`korish` yo'q) kiradi: bosh sahifa uni «Mening reviziyalarim»ga yo'naltiradi.
        user = form.get_user()
        if not (huquqi_bor(user, "korish") or huquqi_bor(user, "reviziya_otkazish")):
            form.add_error(None, KIRISH_YOQ)
            return self.form_invalid(form)
        return super().form_valid(form)


class ChiqishView(auth_views.LogoutView):
    pass
