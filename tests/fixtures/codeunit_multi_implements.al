codeunit 50102 "Multi Interface Impl" implements "IAddress Provider", "INotification Service"
{
    procedure GetAddress(CustomerNo: Code[20]): Text[250]
    begin
        exit('456 Oak Ave');
    end;

    procedure ValidateAddress(var Address: Text[250]): Boolean
    begin
        exit(true);
    end;

    procedure FormatAddress(Address: Text[250]; CountryCode: Code[10]): Text[250]
    begin
        exit(Address);
    end;

    procedure SendNotification(Message: Text[500])
    begin
        // placeholder
    end;
}
