table 50100 "Simple Address"
{
    Caption = 'Simple Address';
    DataPerCompany = true;

    fields
    {
        field(1; "Address Line"; Text[100])
        {
            Caption = 'Address Line';
        }
        field(2; City; Text[50])
        {
            Caption = 'City';
        }
        field(3; "Post Code"; Code[20])
        {
            Caption = 'Post Code';
        }
    }

    keys
    {
        key(PK; "Address Line")
        {
            Clustered = true;
        }
    }
}
