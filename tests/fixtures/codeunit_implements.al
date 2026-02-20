codeunit 50101 "Address Provider" implements "IAddress Provider"
{
    procedure GetAddress(CustomerNo: Code[20]): Text[250]
    begin
        exit('123 Main St, Springfield');
    end;

    procedure ValidateAddress(var Address: Text[250]): Boolean
    begin
        exit(Address <> '');
    end;

    procedure FormatAddress(Address: Text[250]; CountryCode: Code[10]): Text[250]
    begin
        exit(Address + ', ' + CountryCode);
    end;
}
