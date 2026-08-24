from apps.companies.models import Company
from apps.users.models import User

c = Company.objects.get(name="Empresa Beta")
u, criado = User.objects.get_or_create(
    email="qa-admin@beta.com",
    defaults={"full_name": "QA Admin", "role": "company_admin", "company": c},
)
u.set_password("senha123"); u.role = "company_admin"; u.company = c; u.is_active = True
u.save()
print("QA_ADMIN", u.email, "criado" if criado else "atualizado")
