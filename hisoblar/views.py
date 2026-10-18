from django.contrib.auth import views as auth_views

from .huquqlar import huquqi_bor

KIRISH_YOQ = "Panelga kirish huquqi yo'q"


class KirishView(auth_views.LoginView):
    template_name = "hisoblar/kirish.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Parol to'g'ri bo'lsa ham, rol panelga kirishga ruxsat bermasa sessiya ochilmaydi.
        if not huquqi_bor(form.get_user(), "korish"):
            form.add_error(None, KIRISH_YOQ)
            return self.form_invalid(form)
        return super().form_valid(form)


class ChiqishView(auth_views.LogoutView):
    pass
