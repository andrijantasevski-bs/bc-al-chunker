interface "IAddress Provider"
{
    procedure GetAddress(CustomerNo: Code[20]): Text[250];
    procedure ValidateAddress(var Address: Text[250]): Boolean;
    procedure FormatAddress(Address: Text[250]; CountryCode: Code[10]): Text[250];
}
