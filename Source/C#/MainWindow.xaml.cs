using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
//using System.Windows.Shapes;
using CefSharp;
using CefSharp.DevTools.Browser;
using CefSharp.Handler;
using CefSharp.Wpf;

namespace SHTS
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();

            // Path to your local HTML file or other resources
            string filePath = Path.Combine(Directory.GetCurrentDirectory(), "yourfile.html");

            Browser.RequestHandler = new RequestHandler();

            // Ensure the file exists before attempting to load it
            if (File.Exists(filePath))
            {
                // Convert to a URI and load it into the ChromiumWebBrowser
                Browser.Load($"file:///{filePath.Replace('\\', '/')}");
            }
            else
            {
                MessageBox.Show("File not found.");
            }
        }
    }
}