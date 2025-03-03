import factory


class PersonFactory(factory.DjangoModelFactory):
    class Meta:
        model = "people.Person"

    name = factory.Faker("name")
    versions = "[]"
