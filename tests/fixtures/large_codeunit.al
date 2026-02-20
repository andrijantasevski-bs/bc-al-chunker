codeunit 50100 "Address Management"
{
    /// <summary>
    /// Manages address validation and normalization for customer records.
    /// </summary>

    trigger OnRun()
    begin
        Message('Address Management codeunit initialized.');
    end;

    procedure ValidateAddress(var CustAddr: Record "Customer Address")
    begin
        if CustAddr."Address Line 1" = '' then
            Error('Address line is required.');
        if CustAddr.City = '' then
            Error('City is required.');
        if CustAddr."Post Code" = '' then
            Error('Post code is required.');

        NormalizePostCode(CustAddr);
        CustAddr."Is Validated" := true;
        CustAddr.Modify(true);
    end;

    procedure NormalizePostCode(var CustAddr: Record "Customer Address")
    var
        PostCode: Code[20];
    begin
        PostCode := CustAddr."Post Code";
        PostCode := DelChr(PostCode, '=', ' ');
        CustAddr."Post Code" := PostCode;
    end;

    procedure GetFormattedAddress(CustAddr: Record "Customer Address"): Text[250]
    var
        Result: Text[250];
    begin
        Result := CustAddr."Address Line 1";
        if CustAddr.City <> '' then
            Result := Result + ', ' + CustAddr.City;
        if CustAddr.County <> '' then
            Result := Result + ', ' + CustAddr.County;
        if CustAddr."Post Code" <> '' then
            Result := Result + ' ' + CustAddr."Post Code";
        exit(Result);
    end;

    procedure BatchValidateAddresses()
    var
        CustAddr: Record "Customer Address";
    begin
        CustAddr.SetRange("Is Validated", false);
        if CustAddr.FindSet() then
            repeat
                ValidateAddress(CustAddr);
            until CustAddr.Next() = 0;
    end;

    [EventSubscriber(ObjectType::Codeunit, Codeunit::"Customer Mgt.", 'OnAfterInsertCustomer', '', true, true)]
    local procedure OnAfterInsertCustomer(var Customer: Record Customer)
    var
        CustAddr: Record "Customer Address";
    begin
        CustAddr.Init();
        CustAddr."Customer No." := Customer."No.";
        CustAddr.Insert(true);
    end;

    procedure LookupCountry(var CountryCode: Code[10]): Boolean
    var
        Country: Record "Country/Region";
    begin
        if Page.RunModal(Page::"Countries/Regions", Country) = Action::LookupOK then begin
            CountryCode := Country.Code;
            exit(true);
        end;
        exit(false);
    end;

    procedure CheckDuplicateAddress(CustAddr: Record "Customer Address"): Boolean
    var
        ExistingAddr: Record "Customer Address";
    begin
        ExistingAddr.SetRange("Customer No.", CustAddr."Customer No.");
        ExistingAddr.SetRange("Address Line 1", CustAddr."Address Line 1");
        ExistingAddr.SetRange(City, CustAddr.City);
        ExistingAddr.SetRange("Post Code", CustAddr."Post Code");
        exit(not ExistingAddr.IsEmpty());
    end;

    procedure GetAddressCount(CustomerNo: Code[20]): Integer
    var
        CustAddr: Record "Customer Address";
    begin
        CustAddr.SetRange("Customer No.", CustomerNo);
        exit(CustAddr.Count());
    end;

    internal procedure LogAddressChange(CustAddr: Record "Customer Address"; FieldCaption: Text)
    begin
        // Placeholder for logging address changes
        Message('Address field %1 changed for customer %2.', FieldCaption, CustAddr."Customer No.");
    end;

    procedure DeleteInvalidAddresses(CustomerNo: Code[20])
    var
        CustAddr: Record "Customer Address";
    begin
        CustAddr.SetRange("Customer No.", CustomerNo);
        CustAddr.SetRange("Is Validated", false);
        if not CustAddr.IsEmpty() then
            CustAddr.DeleteAll(true);
    end;

    procedure TransferAddress(FromCust: Code[20]; ToCust: Code[20])
    var
        FromAddr: Record "Customer Address";
        ToAddr: Record "Customer Address";
    begin
        FromAddr.SetRange("Customer No.", FromCust);
        if FromAddr.FindSet() then
            repeat
                ToAddr.TransferFields(FromAddr);
                ToAddr."Customer No." := ToCust;
                if not ToAddr.Insert(false) then
                    ToAddr.Modify(false);
            until FromAddr.Next() = 0;
    end;
}
