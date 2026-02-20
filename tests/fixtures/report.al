report 50100 "Customer Address Report"
{
    Caption = 'Customer Address Report';
    DefaultLayout = RDLC;
    UsageCategory = ReportsAndAnalysis;
    ApplicationArea = All;

    dataset
    {
        dataitem(Customer; Customer)
        {
            RequestFilterFields = "No.", "Customer Posting Group";
            column(CustomerNo; "No.")
            {
            }
            column(CustomerName; Name)
            {
            }
            dataitem(CustomerAddress; "Customer Address")
            {
                DataItemLink = "Customer No." = field("No.");
                DataItemTableView = sorting("Customer No.", "Address Line 1");

                column(AddressLine; "Address Line 1")
                {
                }
                column(City; City)
                {
                }
                column(PostCode; "Post Code")
                {
                }
                column(IsValidated; "Is Validated")
                {
                }
            }
        }
    }

    requestpage
    {
        layout
        {
            area(Content)
            {
                group(Options)
                {
                    field(ShowValidatedOnly; ShowValidated)
                    {
                        Caption = 'Show Validated Only';
                        ApplicationArea = All;
                    }
                }
            }
        }
    }

    rendering
    {
        layout(RDLCLayout)
        {
            Type = RDLC;
            LayoutFile = './Layouts/CustomerAddressReport.rdl';
            Caption = 'Customer Address Report (RDLC)';
        }
    }

    var
        ShowValidated: Boolean;

    trigger OnPreReport()
    begin
        if ShowValidated then
            CustomerAddress.SetRange("Is Validated", true);
    end;
}
