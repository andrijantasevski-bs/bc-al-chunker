page 50101 "Customer Address List"
{
    PageType = List;
    SourceTable = "Customer Address";
    Caption = 'Customer Address List';
    Editable = false;
    CardPageId = "Customer Address Card";

    layout
    {
        area(Content)
        {
            repeater(Addresses)
            {
                field("Customer No."; Rec."Customer No.")
                {
                    ApplicationArea = All;
                }
                field("Address Line 1"; Rec."Address Line 1")
                {
                    ApplicationArea = All;
                }
                field(City; Rec.City)
                {
                    ApplicationArea = All;
                }
                field("Post Code"; Rec."Post Code")
                {
                    ApplicationArea = All;
                }
                field("Is Validated"; Rec."Is Validated")
                {
                    ApplicationArea = All;
                }
            }
        }
    }

    views
    {
        view(ValidatedOnly)
        {
            Caption = 'Validated Addresses';
            Filters = where("Is Validated" = const(true));
        }
        view(UnvalidatedOnly)
        {
            Caption = 'Unvalidated Addresses';
            Filters = where("Is Validated" = const(false));
        }
    }

    actions
    {
        area(Processing)
        {
            action(BatchValidate)
            {
                ApplicationArea = All;
                Caption = 'Batch Validate';
                Image = Approve;

                trigger OnAction()
                var
                    AddrMgt: Codeunit "Address Management";
                begin
                    AddrMgt.BatchValidateAddresses();
                    CurrPage.Update(false);
                end;
            }
        }
    }
}
