page 50100 "Customer Address Card"
{
    PageType = Card;
    SourceTable = "Customer Address";
    Caption = 'Customer Address Card';

    layout
    {
        area(Content)
        {
            group(General)
            {
                field("Customer No."; Rec."Customer No.")
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies the customer number.';
                }
                field("Address Line 1"; Rec."Address Line 1")
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies the first line of the address.';
                }
                field(City; Rec.City)
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies the city.';
                }
                field(County; Rec.County)
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies the county.';
                }
                field("Post Code"; Rec."Post Code")
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies the post code.';
                }
            }
            group(Validation)
            {
                field("Is Validated"; Rec."Is Validated")
                {
                    ApplicationArea = All;
                    ToolTip = 'Specifies if the address has been validated.';
                    Editable = false;
                }
            }
        }
    }

    actions
    {
        area(Processing)
        {
            action(ValidateAddress)
            {
                ApplicationArea = All;
                Caption = 'Validate Address';
                ToolTip = 'Validates the current address.';
                Image = Approve;

                trigger OnAction()
                var
                    AddrMgt: Codeunit "Address Management";
                begin
                    AddrMgt.ValidateAddress(Rec);
                    CurrPage.Update(false);
                end;
            }
            action(CopyAddress)
            {
                ApplicationArea = All;
                Caption = 'Copy Address';
                ToolTip = 'Copies the address to clipboard.';
                Image = Copy;

                trigger OnAction()
                var
                    AddrMgt: Codeunit "Address Management";
                    FormattedAddr: Text[250];
                begin
                    FormattedAddr := AddrMgt.GetFormattedAddress(Rec);
                    Message(FormattedAddr);
                end;
            }
        }
        area(Navigation)
        {
            action(CustomerCard)
            {
                ApplicationArea = All;
                Caption = 'Customer Card';
                RunObject = page "Customer Card";
                RunPageLink = "No." = field("Customer No.");
            }
        }
    }

    trigger OnOpenPage()
    begin
        // Page initialization logic
    end;
}
