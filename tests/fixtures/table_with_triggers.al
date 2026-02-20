table 50101 "Customer Address"
{
    Caption = 'Customer Address';
    DataPerCompany = true;

    fields
    {
        field(1; "Customer No."; Code[20])
        {
            Caption = 'Customer No.';
            TableRelation = Customer;
        }
        field(2; "Address Line 1"; Text[100])
        {
            Caption = 'Address Line 1';

            trigger OnValidate()
            begin
                if "Address Line 1" = '' then
                    Error('Address Line 1 must not be empty.');
            end;
        }
        field(3; City; Text[50])
        {
            Caption = 'City';

            trigger OnValidate()
            begin
                ValidateCity(City);
            end;
        }
        field(4; County; Text[30])
        {
            Caption = 'County';
        }
        field(5; "Post Code"; Code[20])
        {
            Caption = 'Post Code';
        }
        field(6; "Country Code"; Code[10])
        {
            Caption = 'Country Code';
            TableRelation = "Country/Region";
        }
        field(7; "Is Validated"; Boolean)
        {
            Caption = 'Address Validated';
            InitValue = false;
        }
    }

    keys
    {
        key(PK; "Customer No.", "Address Line 1")
        {
            Clustered = true;
        }
        key(PostCodeIdx; "Post Code")
        {
        }
    }

    trigger OnInsert()
    begin
        if "Customer No." = '' then
            Error('Customer No. must be filled in.');
    end;

    trigger OnModify()
    begin
        "Is Validated" := false;
    end;

    local procedure ValidateCity(CityName: Text[50])
    begin
        if StrLen(CityName) < 2 then
            Error('City name is too short.');
    end;
}
